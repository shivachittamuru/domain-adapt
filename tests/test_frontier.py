import json
import sqlite3
from types import SimpleNamespace

import pytest

from domain_adapt.frontier import (
    build_model_input,
    build_schema_context,
    load_baseline_config,
    request_sql,
)


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    connection.executescript(
        """
        CREATE TABLE zebra (
            second_column TEXT,
            first_column INTEGER
        );
        CREATE TABLE alpha (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            secret_value TEXT
        );
        INSERT INTO alpha (secret_value)
        VALUES ('must-not-appear');
        CREATE TABLE "quoted""table" (
            value REAL
        );
        """
    )
    yield connection
    connection.close()


def test_build_schema_context_uses_only_ordered_schema_metadata(conn):
    schema_context = build_schema_context(conn)

    assert schema_context == (
        "alpha(id INTEGER, secret_value TEXT)\n"
        'quoted"table(value REAL)\n'
        "zebra(second_column TEXT, first_column INTEGER)"
    )
    assert "sqlite_sequence" not in schema_context
    assert "must-not-appear" not in schema_context


def test_build_model_input_uses_exact_prompt_format():
    assert build_model_input(
        "alpha(id INTEGER)\nzebra(name TEXT)",
        "Which records exist?",
    ) == (
        "Database schema:\n\n"
        "alpha(id INTEGER)\n"
        "zebra(name TEXT)\n\n"
        "Question:\n\n"
        "Which records exist?"
    )


class FakeResponses:
    def __init__(self, output_text):
        self.response = SimpleNamespace(output_text=output_text)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


class FakeClient:
    def __init__(self, output_text):
        self.responses = FakeResponses(output_text)


@pytest.mark.parametrize(
    ("output_text", "expected_sql"),
    [
        (
            "\n  SELECT  *\nFROM alpha;  \n",
            "SELECT  *\nFROM alpha;",
        ),
        (
            "\n```sql\nSELECT * FROM alpha;\n```\n",
            "```sql\nSELECT * FROM alpha;\n```",
        ),
        (
            " \nthis is not valid SQL\n ",
            "this is not valid SQL",
        ),
    ],
)
def test_request_sql_preserves_candidate_content(
    output_text,
    expected_sql,
):
    client = FakeClient(output_text)

    response, candidate_sql = request_sql(
        client=client,
        deployment_name="frontier-deployment",
        instructions="Return SQL.",
        schema_context="alpha(id INTEGER)",
        question="Which records exist?",
        max_output_tokens=2000,
    )

    assert response is client.responses.response
    assert candidate_sql == expected_sql
    assert client.responses.calls == [
        {
            "model": "frontier-deployment",
            "instructions": "Return SQL.",
            "input": (
                "Database schema:\n\n"
                "alpha(id INTEGER)\n\n"
                "Question:\n\n"
                "Which records exist?"
            ),
            "max_output_tokens": 2000,
            "store": False,
        }
    ]


def test_load_baseline_config(tmp_path):
    config_path = tmp_path / "baseline.json"
    expected = {
        "name": "test-baseline",
        "max_output_tokens": 2000,
    }
    config_path.write_text(json.dumps(expected), encoding="utf-8")

    assert load_baseline_config(config_path) == expected
