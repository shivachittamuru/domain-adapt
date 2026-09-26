import pytest

from domain_adapt.finch import make_reference_compatible


@pytest.mark.parametrize(
    ("original", "expected", "expected_rules"),
    [
        (
            "SELECT STRFTIME('%y', t.date) FROM loan AS t",
            "SELECT STRFTIME('%Y', t.date) FROM loan AS t",
            ["sqlite_four_digit_year"],
        ),
        (
            "SELECT * FROM client AS t WHERE t.gender = 'm'",
            (
                "SELECT * FROM client AS t "
                "WHERE t.gender = 'm' COLLATE NOCASE"
            ),
            ["case_insensitive_text_equality"],
        ),
        (
            """
            SELECT *
            FROM loan AS t
            WHERE STRFTIME('%y', t.date) = '1997'
              AND t.status = 'c'
            """,
            """
            SELECT *
            FROM loan AS t
            WHERE STRFTIME('%Y', t.date) = '1997'
              AND t.status = 'c' COLLATE NOCASE
            """,
            [
                "sqlite_four_digit_year",
                "case_insensitive_text_equality",
            ],
        ),
        (
            "SELECT COUNT(*) FROM loan",
            "SELECT COUNT(*) FROM loan",
            [],
        ),
    ],
)
def test_make_reference_compatible(
    original,
    expected,
    expected_rules,
):
    compatible, rules = make_reference_compatible(original)

    assert compatible == expected
    assert rules == expected_rules


def test_compatibility_transformation_is_idempotent():
    original = """
        SELECT *
        FROM client AS t
        WHERE t.gender = 'm'
          AND STRFTIME('%y', t.date) = '1997'
    """

    first_sql, first_rules = make_reference_compatible(original)
    second_sql, second_rules = make_reference_compatible(first_sql)

    assert first_rules == [
        "sqlite_four_digit_year",
        "case_insensitive_text_equality",
    ]
    assert second_sql == first_sql
    assert second_rules == []