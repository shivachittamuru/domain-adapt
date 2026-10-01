from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest

from domain_adapt.context_engineering import (
    load_context_engineering_config,
    request_context_engineered_sql,
    request_frontier_context_engineered_sql,
    unwrap_single_sql_fence,
    validate_context_engineering_config,
)
from domain_adapt.frontier import build_model_input


CONFIG_PATH = (
    Path(__file__).parents[1] / "configs" / "slm_context_engineered_v1.json"
)
INSTRUCTIONS_SHA256 = (
    "175e0489882789131bba788ad087f79e24a2207460d934778a16e04d7f265509"
)
SCHEMA_CONTEXT_SHA256 = (
    "634503b9d904730790555dfeabb2a81a920293a9d747416a04e372e122d7b987"
)


class FakeCompletions:
    def __init__(self, content):
        message = SimpleNamespace(content=content)
        choice = SimpleNamespace(message=message)
        self.response = SimpleNamespace(choices=[choice])
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


class FakeChat:
    def __init__(self, content):
        self.completions = FakeCompletions(content)


class FakeClient:
    def __init__(self, content):
        self.chat = FakeChat(content)


class FakeResponses:
    def __init__(self, output_text):
        self.response = SimpleNamespace(output_text=output_text)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


class FakeFrontierClient:
    def __init__(self, output_text):
        self.responses = FakeResponses(output_text)


@pytest.fixture
def config():
    return load_context_engineering_config(CONFIG_PATH)


def test_configuration_loads_successfully(config):
    assert config["name"] == "ministral-3b-context-engineered-v1"


def test_exact_instruction_hash(config):
    assert sha256(config["instructions"].encode("utf-8")).hexdigest() == (
        INSTRUCTIONS_SHA256
    )


def test_exact_context_hash(config):
    assert sha256(config["schema_context"].encode("utf-8")).hexdigest() == (
        SCHEMA_CONTEXT_SHA256
    )


@pytest.mark.parametrize("key", ["instructions", "schema_context"])
def test_altered_frozen_text_is_rejected(config, key):
    altered = deepcopy(config)
    altered[key] += " "

    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        validate_context_engineering_config(altered)


@pytest.mark.parametrize(
    "key",
    ["candidate_sql_repair", "retry_incorrect_answers"],
)
def test_repair_and_retry_are_rejected_if_enabled(config, key):
    altered = deepcopy(config)
    altered["generation"][key] = True

    with pytest.raises(ValueError, match=key):
        validate_context_engineering_config(altered)


def test_multiple_attempts_are_rejected(config):
    altered = deepcopy(config)
    altered["generation"]["attempts_per_question"] = 2

    with pytest.raises(ValueError, match="attempts_per_question"):
        validate_context_engineering_config(altered)


def test_changed_output_normalization_is_rejected(config):
    altered = deepcopy(config)
    altered["output_normalization"] = "strip all Markdown"

    with pytest.raises(ValueError, match="output_normalization"):
        validate_context_engineering_config(altered)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("SELECT 1;", ("SELECT 1;", False)),
        ("```sql\nSELECT 1;\n```", ("SELECT 1;", True)),
        ("```sqlite\nSELECT 1;\n```", ("SELECT 1;", True)),
        ("```\nSELECT 1;\n```", ("SELECT 1;", True)),
        ("\n  ```sql\n SELECT 1; \n```  \n", ("SELECT 1;", True)),
        (None, ("", False)),
    ],
)
def test_strict_fence_normalization(text, expected):
    assert unwrap_single_sql_fence(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "Here is SQL:\n```sql\nSELECT 1;\n```",
        "```sql\nSELECT 1;\n```\nTrailing text",
        "```sql\n```\nSELECT 1;\n```\n```",
        "```sql\n\n```",
    ],
)
def test_non_single_fences_are_not_unwrapped(text):
    assert unwrap_single_sql_fence(text) == (text.strip(), False)


def test_wrapper_uses_existing_slm_contract_once(config):
    client = FakeClient("```sql\nSELECT 1;\n```")
    question = "Return one."

    response, raw_sql, normalized_sql, was_unwrapped = (
        request_context_engineered_sql(
            client=client,
            deployment_name="slm-deployment",
            question=question,
            config=config,
        )
    )

    assert response is client.chat.completions.response
    assert raw_sql == "```sql\nSELECT 1;\n```"
    assert normalized_sql == "SELECT 1;"
    assert was_unwrapped is True
    assert client.chat.completions.calls == [
        {
            "model": "slm-deployment",
            "messages": [
                {
                    "role": "system",
                    "content": config["instructions"],
                },
                {
                    "role": "user",
                    "content": build_model_input(
                        config["schema_context"],
                        question,
                    ),
                },
            ],
            "max_tokens": config["max_tokens"],
        }
    ]


def test_invalid_config_prevents_model_call(config):
    client = FakeClient("SELECT 1;")
    altered = deepcopy(config)
    altered["generation"]["candidate_sql_repair"] = True

    with pytest.raises(ValueError, match="candidate_sql_repair"):
        request_context_engineered_sql(
            client=client,
            deployment_name="slm-deployment",
            question="Return one.",
            config=altered,
        )

    assert client.chat.completions.calls == []


def test_frontier_wrapper_uses_same_context_contract_once(config):
    client = FakeFrontierClient("```sql\nSELECT 1;\n```")
    question = "Return one."

    response, raw_sql, normalized_sql, was_unwrapped = (
        request_frontier_context_engineered_sql(
            client=client,
            deployment_name="frontier-deployment",
            question=question,
            config=config,
        )
    )

    assert response is client.responses.response
    assert raw_sql == "```sql\nSELECT 1;\n```"
    assert normalized_sql == "SELECT 1;"
    assert was_unwrapped is True
    assert client.responses.calls == [
        {
            "model": "frontier-deployment",
            "instructions": config["instructions"],
            "input": build_model_input(
                config["schema_context"],
                question,
            ),
            "max_output_tokens": config["max_tokens"],
            "store": False,
        }
    ]
