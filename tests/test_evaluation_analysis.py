import pytest

from domain_adapt.evaluation_analysis import (
    compare_runs,
    failure_category,
    index_results,
    is_executable,
    summarize_results,
)


def result(
    question_id,
    *,
    passed=False,
    reason="unordered results differ",
    difficulty="easy",
    api_error=None,
    usage=None,
    latency_seconds=1.0,
):
    return {
        "question_id": question_id,
        "difficulty": difficulty,
        "passed": passed,
        "reason": reason,
        "api_error": api_error,
        "usage": usage or {},
        "latency_seconds": latency_seconds,
        "output_envelope_normalized": False,
        "response_model": "model-v1" if api_error is None else None,
    }


def test_failure_categories_and_executability():
    execution_failure = result(
        1,
        reason="candidate execution failed: no such column",
    )
    column_failure = result(2, reason="column count differs: 1 != 2")
    api_failure = result(3, reason="model request failed", api_error="boom")

    assert is_executable(execution_failure) is False
    assert is_executable(column_failure) is True
    assert failure_category(execution_failure) == "candidate_execution_failed"
    assert failure_category(column_failure) == "column_count_differs"
    assert failure_category(api_failure) == "api_error"


def test_summary_is_deterministic():
    results = [
        result(
            1,
            passed=True,
            reason="unordered results match",
            usage={
                "prompt_tokens": 10,
                "completion_tokens": 2,
                "total_tokens": 12,
            },
            latency_seconds=0.5,
        ),
        result(
            2,
            difficulty="medium",
            reason="candidate execution failed: syntax error",
            usage={
                "prompt_tokens": 11,
                "completion_tokens": 3,
                "total_tokens": 14,
            },
            latency_seconds=1.5,
        ),
    ]

    summary = summarize_results(results)

    assert summary["passed"] == 1
    assert summary["total"] == 2
    assert summary["executable"] == 1
    assert summary["failure_categories"] == {
        "candidate_execution_failed": 1,
    }
    assert summary["token_usage"]["total_tokens"] == 26
    assert summary["median_latency_seconds"] == 1.0


def test_duplicate_question_ids_are_rejected():
    with pytest.raises(ValueError, match="Duplicate question ID"):
        index_results([result(1), result(1)])


def test_run_comparison_reports_transitions():
    baseline = [
        result(1),
        result(2, passed=True, reason="unordered results match"),
    ]
    candidate = [
        result(1, passed=True, reason="unordered results match"),
        result(2),
    ]

    comparison = compare_runs(baseline, candidate)

    assert [row["transition"] for row in comparison] == [
        "improved",
        "regressed",
    ]


def test_run_comparison_requires_the_same_questions():
    with pytest.raises(ValueError, match="Run question IDs differ"):
        compare_runs([result(1)], [result(2)])
