from typing import Any

from .http import post_json


def call_gemini(api_key: str, model: str, messages: list[dict[str, Any]]) -> str:
    contents = []
    system_instruction = None

    for message in messages:
        role = message["role"]
        content = message["content"]

        if role == "system":
            system_instruction = {"parts": [{"text": content}]}
            continue

        contents.append(
            {
                "role": "model" if role == "assistant" else "user",
                "parts": [{"text": content}],
            }
        )

    body: dict[str, Any] = {"contents": contents}
    if system_instruction:
        body["systemInstruction"] = system_instruction

    data = post_json(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        headers={"x-goog-api-key": api_key},
        body=body,
    )

    try:
        parts = data["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("Gemini response did not include text output.") from exc

    text = "".join(part.get("text", "") for part in parts)
    if not text:
        raise RuntimeError("Gemini response text was empty.")
    return text
