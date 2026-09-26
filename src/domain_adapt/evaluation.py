from collections import Counter
from dataclasses import dataclass
import math
import sqlite3

import sqlglot
from sqlglot.errors import ParseError


FLOAT_DECIMAL_PLACES = 6


@dataclass(frozen=True)
class QueryResult:
    rows: tuple[tuple[object, ...], ...]
    column_count: int


@dataclass(frozen=True)
class ComparisonResult:
    equivalent: bool
    reason: str
    expected_row_count: int | None
    candidate_row_count: int | None


def normalize_value(value: object) -> object:
    """Convert a SQLite value into a stable comparison value."""
    if isinstance(value, float):
        if math.isnan(value):
            return ("float", "nan")

        if math.isinf(value):
            return ("float", "inf" if value > 0 else "-inf")

        rounded = round(value, FLOAT_DECIMAL_PLACES)
        return 0.0 if rounded == 0 else rounded

    return value


def execute_sql(
    conn: sqlite3.Connection,
    sql: str,
) -> QueryResult:
    """Execute SQL and return normalized rows and column count."""
    cursor = conn.execute(sql)
    rows = cursor.fetchall()

    normalized_rows = tuple(
        tuple(normalize_value(value) for value in row)
        for row in rows
    )

    return QueryResult(
        rows=normalized_rows,
        column_count=len(cursor.description or []),
    )


def reference_requires_order(sql: str) -> bool:
    """Return whether ORDER BY controls the final query result."""
    try:
        expression = sqlglot.parse_one(sql, read="sqlite")
    except ParseError as error:
        raise ValueError(
            f"Unable to determine result ordering: {error}"
        ) from error

    return expression.args.get("order") is not None


def compare_sql_results(
    conn: sqlite3.Connection,
    reference_sql: str,
    candidate_sql: str,
) -> ComparisonResult:
    """Execute two queries and compare their returned answers."""
    try:
        expected = execute_sql(conn, reference_sql)
    except sqlite3.Error as error:
        return ComparisonResult(
            equivalent=False,
            reason=f"reference execution failed: {error}",
            expected_row_count=None,
            candidate_row_count=None,
        )

    try:
        candidate = execute_sql(conn, candidate_sql)
    except sqlite3.Error as error:
        return ComparisonResult(
            equivalent=False,
            reason=f"candidate execution failed: {error}",
            expected_row_count=len(expected.rows),
            candidate_row_count=None,
        )

    if expected.column_count != candidate.column_count:
        return ComparisonResult(
            equivalent=False,
            reason=(
                "column count differs: "
                f"{expected.column_count} != {candidate.column_count}"
            ),
            expected_row_count=len(expected.rows),
            candidate_row_count=len(candidate.rows),
        )

    if reference_requires_order(reference_sql):
        equivalent = expected.rows == candidate.rows
        comparison_mode = "ordered"
    else:
        equivalent = Counter(expected.rows) == Counter(candidate.rows)
        comparison_mode = "unordered"

    return ComparisonResult(
        equivalent=equivalent,
        reason=(
            f"{comparison_mode} results match"
            if equivalent
            else f"{comparison_mode} results differ"
        ),
        expected_row_count=len(expected.rows),
        candidate_row_count=len(candidate.rows),
    )