"""Deterministic analysis helpers for saved evaluation runs.

The functions in this module never call a model or execute SQL.  They turn the
per-question records produced by an evaluation run into stable summaries and
baseline/candidate comparisons that can be reused across notebooks.
"""

from collections import Counter
from statistics import median
from typing import Any, Iterable, Sequence


DEFAULT_DIFFICULTIES = ("easy", "medium", "hard")


def is_executable(result: dict[str, Any]) -> bool:
    """Return whether a candidate reached a comparable SQL result."""
    reason = result.get("reason") or ""
    return (
        result.get("api_error") is None
        and not reason.startswith("candidate execution failed")
        and not reason.startswith("model request failed")
    )


def failure_category(result: dict[str, Any]) -> str:
    """Collapse a detailed failure reason into a stable analysis category."""
    if result.get("api_error") is not None:
        return "api_error"

    reason = result.get("reason") or "unknown failure"

    if reason.startswith("candidate execution failed"):
        return "candidate_execution_failed"
    if reason.startswith("column count differs"):
        return "column_count_differs"
    if reason == "ordered results differ":
        return "ordered_results_differ"
    if reason == "unordered results differ":
        return "unordered_results_differ"

    return reason.strip().lower().replace(" ", "_")


def index_results(
    results: Iterable[dict[str, Any]],
) -> dict[int, dict[str, Any]]:
    """Index results by question ID and reject duplicate IDs."""
    indexed: dict[int, dict[str, Any]] = {}

    for result in results:
        question_id = result["question_id"]
        if question_id in indexed:
            raise ValueError(f"Duplicate question ID: {question_id}")
        indexed[question_id] = result

    return indexed


def summarize_results(
    results: Sequence[dict[str, Any]],
    difficulties: Sequence[str] = DEFAULT_DIFFICULTIES,
) -> dict[str, Any]:
    """Build the common accuracy, executability, latency, and usage summary."""
    if not results:
        raise ValueError("Cannot summarize an empty evaluation run")

    index_results(results)
    total = len(results)
    passed = sum(bool(result.get("passed")) for result in results)
    executable = sum(is_executable(result) for result in results)

    by_difficulty: dict[str, dict[str, Any]] = {}
    for difficulty in difficulties:
        subset = [
            result
            for result in results
            if result.get("difficulty") == difficulty
        ]
        if not subset:
            continue

        subset_passed = sum(
            bool(result.get("passed")) for result in subset
        )
        by_difficulty[difficulty] = {
            "passed": subset_passed,
            "total": len(subset),
            "accuracy": subset_passed / len(subset),
        }

    failure_categories = Counter(
        failure_category(result)
        for result in results
        if not result.get("passed")
    )

    token_names = (
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
    )
    token_usage = {
        token_name: sum(
            int(result.get("usage", {}).get(token_name, 0) or 0)
            for result in results
        )
        for token_name in token_names
    }

    latencies = [
        float(result["latency_seconds"])
        for result in results
        if result.get("latency_seconds") is not None
    ]

    return {
        "passed": passed,
        "total": total,
        "accuracy": passed / total,
        "executable": executable,
        "executable_rate": executable / total,
        "by_difficulty": by_difficulty,
        "failure_categories": dict(failure_categories),
        "api_errors": sum(
            result.get("api_error") is not None for result in results
        ),
        "strictly_unwrapped_outputs": sum(
            bool(result.get("output_envelope_normalized"))
            for result in results
        ),
        "observed_response_models": sorted(
            {
                result["response_model"]
                for result in results
                if result.get("response_model")
            }
        ),
        "token_usage": token_usage,
        "median_latency_seconds": (
            median(latencies) if latencies else None
        ),
    }


def compare_runs(
    baseline_results: Sequence[dict[str, Any]],
    candidate_results: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Compare two runs with the same question IDs."""
    baseline = index_results(baseline_results)
    candidate = index_results(candidate_results)

    if baseline.keys() != candidate.keys():
        missing = sorted(baseline.keys() - candidate.keys())
        unexpected = sorted(candidate.keys() - baseline.keys())
        raise ValueError(
            "Run question IDs differ; "
            f"missing={missing}, unexpected={unexpected}"
        )

    comparisons = []
    for question_id in sorted(baseline):
        base = baseline[question_id]
        current = candidate[question_id]
        base_passed = bool(base.get("passed"))
        current_passed = bool(current.get("passed"))

        if not base_passed and current_passed:
            transition = "improved"
        elif base_passed and not current_passed:
            transition = "regressed"
        elif current_passed:
            transition = "still_passes"
        else:
            transition = "still_fails"

        comparisons.append(
            {
                "question_id": question_id,
                "difficulty": current.get("difficulty"),
                "baseline_passed": base_passed,
                "baseline_executable": is_executable(base),
                "candidate_passed": current_passed,
                "candidate_executable": is_executable(current),
                "transition": transition,
                "baseline_reason": base.get("reason"),
                "candidate_reason": current.get("reason"),
            }
        )

    return comparisons
