from pathlib import Path
from typing import Any
import json
import sqlite3


def load_baseline_config(path: str | Path) -> dict[str, Any]:
    """Load a frontier baseline configuration from JSON."""
    with Path(path).open(encoding="utf-8") as config_file:
        return json.load(config_file)


def _quote_sqlite_identifier(identifier: str) -> str:
    return f'"{identifier.replace('"', '""')}"'


def build_schema_context(conn: sqlite3.Connection) -> str:
    """Build the minimal schema context used by the frontier baseline."""
    table_names = sorted(
        row[0]
        for row in conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            """
        )
        if not row[0].startswith("sqlite_")
    )

    schema_lines = []

    for table_name in table_names:
        columns = conn.execute(
            f"PRAGMA table_info({_quote_sqlite_identifier(table_name)})"
        ).fetchall()
        column_definitions = ", ".join(
            f"{column[1]} {column[2]}"
            for column in columns
        )
        schema_lines.append(f"{table_name}({column_definitions})")

    return "\n".join(schema_lines)


def build_model_input(schema_context: str, question: str) -> str:
    """Build the exact user input sent to the frontier model."""
    return (
        "Database schema:\n\n"
        f"{schema_context}\n\n"
        "Question:\n\n"
        f"{question}"
    )


def request_sql(
    *,
    client: Any,
    deployment_name: str,
    instructions: str,
    schema_context: str,
    question: str,
    max_output_tokens: int,
) -> tuple[Any, str]:
    """Request one SQL candidate without parsing or repairing the output."""
    response = client.responses.create(
        model=deployment_name,
        instructions=instructions,
        input=build_model_input(schema_context, question),
        max_output_tokens=max_output_tokens,
        store=False,
    )

    return response, response.output_text.strip()
