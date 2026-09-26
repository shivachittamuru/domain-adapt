import sqlite3

import pytest

from domain_adapt.evaluation import (
    compare_sql_results,
    reference_requires_order,
)


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    yield connection
    connection.close()


@pytest.mark.parametrize(
    ("reference_sql", "candidate_sql", "expected"),
    [
        (
            "SELECT 1 UNION ALL SELECT 2",
            "SELECT 2 UNION ALL SELECT 1",
            True,
        ),
        (
            """
            SELECT 1 AS value
            UNION ALL
            SELECT 2
            ORDER BY value ASC
            """,
            """
            SELECT 1 AS value
            UNION ALL
            SELECT 2
            ORDER BY value DESC
            """,
            False,
        ),
        (
            "SELECT 1 UNION ALL SELECT 1",
            "SELECT 1",
            False,
        ),
        (
            "SELECT 1.0 / 3.0",
            "SELECT 0.3333334",
            True,
        ),
        (
            "SELECT 1",
            "SELECT 2",
            False,
        ),
        (
            "SELECT 1",
            "SELECT missing_column",
            False,
        ),
    ],
)
def test_result_equivalence(
    conn,
    reference_sql,
    candidate_sql,
    expected,
):
    comparison = compare_sql_results(
        conn,
        reference_sql,
        candidate_sql,
    )

    assert comparison.equivalent is expected


def test_order_detection_understands_query_structure():
    top_level_order = """
        SELECT account_id
        FROM account
        ORDER BY account_id
    """

    nested_order_only = """
        SELECT COUNT(*)
        FROM (
            SELECT account_id
            FROM account
            ORDER BY account_id
        )
    """

    assert reference_requires_order(top_level_order) is True
    assert reference_requires_order(nested_order_only) is False


def test_column_count_must_match(conn):
    comparison = compare_sql_results(
        conn,
        reference_sql="SELECT 1",
        candidate_sql="SELECT 1, 2",
    )

    assert comparison.equivalent is False
    assert comparison.reason == "column count differs: 1 != 2"