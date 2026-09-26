from typing import Any

from domain_adapt.frontier import build_model_input


def request_sql(
    *,
    client: Any,
    deployment_name: str,
    instructions: str,
    schema_context: str,
    question: str,
    max_tokens: int,
) -> tuple[Any, str]:
    """Request one SQL candidate from the SLM without modifying its content."""
    response = client.chat.completions.create(
        model=deployment_name,
        messages=[
            {
                "role": "system",
                "content": instructions,
            },
            {
                "role": "user",
                "content": build_model_input(
                    schema_context,
                    question,
                ),
            },
        ],
        max_tokens=max_tokens,
    )

    return response, (response.choices[0].message.content or "").strip()
