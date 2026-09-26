import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from domain_adapt.frontier import build_model_input
from domain_adapt.slm import request_sql


CONFIGS_DIR = Path(__file__).parents[1] / "configs"


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


def load_config(name):
    with (CONFIGS_DIR / name).open(encoding="utf-8") as config_file:
        return json.load(config_file)


def test_slm_instructions_match_frontier_instructions():
    frontier_config = load_config("frontier_baseline_v1.json")
    slm_config = load_config("slm_baseline_v1.json")

    assert slm_config["instructions"] == frontier_config["instructions"]


@pytest.mark.parametrize(
    ("content", "expected_sql"),
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
        (
            None,
            "",
        ),
    ],
)
def test_request_sql_uses_exact_chat_contract(content, expected_sql):
    client = FakeClient(content)
    schema_context = "alpha(id INTEGER)"
    question = "Which records exist?"

    response, candidate_sql = request_sql(
        client=client,
        deployment_name="slm-deployment",
        instructions="Return SQL.",
        schema_context=schema_context,
        question=question,
        max_tokens=2000,
    )

    assert response is client.chat.completions.response
    assert candidate_sql == expected_sql
    assert client.chat.completions.calls == [
        {
            "model": "slm-deployment",
            "messages": [
                {
                    "role": "system",
                    "content": "Return SQL.",
                },
                {
                    "role": "user",
                    "content": build_model_input(
                        schema_context,
                        question,
                    ),
                },
            ],
            "max_tokens": 2000,
        }
    ]
