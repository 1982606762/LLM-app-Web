from typing import Any

from .http import post_json


def call_anthropic(api_key: str, model: str, messages: list[dict[str, Any]]) -> str:
    system_parts: list[str] = []
    conversation: list[dict[str, str]] = []

    for message in messages:
        role = message["role"]
        content = message["content"]

        if role == "system":
            system_parts.append(content)
            continue

        conversation.append(
            {
                "role": "assistant" if role == "assistant" else "user",
                "content": content,
            }
        )

    body: dict[str, Any] = {
        "model": model,
        "max_tokens": 1024,
        "messages": conversation,
    }
    if system_parts:
        body["system"] = "\n\n".join(system_parts)

    data = post_json(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        body=body,
    )

    text_parts = [
        block.get("text", "")
        for block in data.get("content", [])
        if block.get("type") == "text"
    ]
    if text_parts:
        return "\n".join(text_parts)

    raise RuntimeError("Anthropic response did not include text output.")
