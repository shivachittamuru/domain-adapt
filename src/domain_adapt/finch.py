import re


_YEAR_FORMAT_PATTERN = re.compile(
    r"(?i:STRFTIME)\(\s*'%y'\s*,"
)

_TEXT_EQUALITY_PATTERN = re.compile(
    r"\b("
    r"[A-Za-z_][A-Za-z0-9_]*"
    r"(?:\.[A-Za-z_][A-Za-z0-9_]*)?"
    r")"
    r"\s*=\s*"
    r"('(?:''|[^'])*')"
    r"(?!\s+COLLATE\s+NOCASE)",
    flags=re.IGNORECASE,
)


def make_reference_compatible(
    sql: str,
) -> tuple[str, list[str]]:
    """Repair known FINCH reference-SQL/database incompatibilities.

    These transformations are intended only for FINCH reference SQL.
    Candidate or model-generated SQL must not pass through this function.
    """
    compatible = sql
    applied_rules = []

    updated = _YEAR_FORMAT_PATTERN.sub(
        "STRFTIME('%Y',",
        compatible,
    )
    if updated != compatible:
        applied_rules.append("sqlite_four_digit_year")
        compatible = updated

    updated = _TEXT_EQUALITY_PATTERN.sub(
        r"\1 = \2 COLLATE NOCASE",
        compatible,
    )
    if updated != compatible:
        applied_rules.append("case_insensitive_text_equality")
        compatible = updated

    return compatible, applied_rules