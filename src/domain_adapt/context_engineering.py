import hashlib
import json
from pathlib import Path
from typing import Any

from domain_adapt.slm import request_sql


EXPECTED_OUTPUT_NORMALIZATION = "strict single surrounding SQL-fence unwrap"


def load_context_engineering_config(path: str | Path) -> dict[str, Any]:
    """Load and validate a context-engineered SLM configuration."""
    with Path(path).open(encoding="utf-8") as config_file:
        config = json.load(config_file)

    validate_context_engineering_config(config)
    return config


def _require_text(config: dict[str, Any], key: str) -> str:
    value = config.get(key)
    if not isinstance(value, str):
        raise ValueError(f"Configuration field {key!r} must be a string")
    return value


def validate_context_engineering_config(config: dict[str, Any]) -> None:
    """Validate the frozen Milestone 5 context-engineering contract."""
    instructions = _require_text(config, "instructions")
    schema_context = _require_text(config, "schema_context")
    expected_instructions_hash = _require_text(config, "instructions_sha256")
    expected_context_hash = _require_text(config, "schema_context_sha256")

    actual_instructions_hash = hashlib.sha256(
        instructions.encode("utf-8")
    ).hexdigest()
    if actual_instructions_hash != expected_instructions_hash:
        raise ValueError(
            "Instructions SHA-256 mismatch: "
            f"expected {expected_instructions_hash}, got {actual_instructions_hash}"
        )

    actual_context_hash = hashlib.sha256(
        schema_context.encode("utf-8")
    ).hexdigest()
    if actual_context_hash != expected_context_hash:
        raise ValueError(
            "Schema context SHA-256 mismatch: "
            f"expected {expected_context_hash}, got {actual_context_hash}"
        )

    generation = config.get("generation")
    if not isinstance(generation, dict):
        raise ValueError("Configuration field 'generation' must be an object")

    attempts = generation.get("attempts_per_question")
    if type(attempts) is not int or attempts != 1:
        raise ValueError("attempts_per_question must be exactly 1")
    if generation.get("temperature") != "provider_default":
        raise ValueError("temperature must be provider_default")
    if generation.get("candidate_sql_repair") is not False:
        raise ValueError("candidate_sql_repair must be false")
    if generation.get("retry_incorrect_answers") is not False:
        raise ValueError("retry_incorrect_answers must be false")
    if config.get("output_normalization") != EXPECTED_OUTPUT_NORMALIZATION:
        raise ValueError(
            "output_normalization must specify strict single surrounding "
            "SQL-fence unwrap"
        )


def unwrap_single_sql_fence(text: str | None) -> tuple[str, bool]:
    """Remove one surrounding SQL fence and nothing else."""
    stripped = (text or "").strip()
    lines = stripped.splitlines()

    if len(lines) < 3:
        return stripped, False

    opening = lines[0].strip().casefold()
    closing = lines[-1].strip()

    if opening not in {
        "```",
        "```sql",
        "```sqlite",
    }:
        return stripped, False

    if closing != "```":
        return stripped, False

    inner_lines = lines[1:-1]

    if any("```" in line for line in inner_lines):
        return stripped, False

    inner_sql = "\n".join(inner_lines).strip()

    if not inner_sql:
        return stripped, False

    return inner_sql, True


def request_context_engineered_sql(
    *,
    client: Any,
    deployment_name: str,
    question: str,
    config: dict[str, Any],
) -> tuple[Any, str, str, bool]:
    """Request and strictly normalize one context-engineered SQL candidate."""
    validate_context_engineering_config(config)
    response, raw_sql = request_sql(
        client=client,
        deployment_name=deployment_name,
        instructions=config["instructions"],
        schema_context=config["schema_context"],
        question=question,
        max_tokens=config["max_tokens"],
    )
    normalized_sql, was_unwrapped = unwrap_single_sql_fence(raw_sql)
    return response, raw_sql, normalized_sql, was_unwrapped
