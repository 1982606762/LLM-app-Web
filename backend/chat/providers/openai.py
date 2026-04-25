from typing import Any

from .http import post_json


def call_openai(api_key: str, model: str, messages: list[dict[str, Any]]) -> str:
    data = post_json(
        "https://api.openai.com/v1/responses",
        headers={"Authorization": f"Bearer {api_key}"},
        body={
            "model": model,
            "input": [
                {
                    "role": message["role"],
                    "content": message["content"],
                }
                for message in messages
            ],
        },
    )

    if isinstance(data.get("output_text"), str):
        return data["output_text"]

    text_parts: list[str] = []
    for item in data.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"}:
                text_parts.append(content.get("text", ""))

    if text_parts:
        return "\n".join(text_parts)

    raise RuntimeError("OpenAI response did not include text output.")
