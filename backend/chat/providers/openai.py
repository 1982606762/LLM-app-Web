import json
from collections.abc import Iterator
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

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


def stream_openai(api_key: str, model: str, messages: list[dict[str, Any]]) -> Iterator[str]:
    request = Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(
            {
                "model": model,
                "stream": True,
                "input": [
                    {
                        "role": message["role"],
                        "content": message["content"],
                    }
                    for message in messages
                ],
            }
        ).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        response = urlopen(request, timeout=60)
    except HTTPError as exc:
        details = exc.read().decode("utf-8")
        raise RuntimeError(f"Provider returned HTTP {exc.code}: {details}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach provider: {exc.reason}") from exc

    def events() -> Iterator[str]:
        data_lines: list[str] = []

        with response:
            for raw_line in response:
                line = raw_line.decode("utf-8").strip()

                if not line:
                    if data_lines:
                        yield from parse_openai_stream_event("\n".join(data_lines))
                        data_lines = []
                    continue

                if line.startswith("data:"):
                    data_lines.append(line.removeprefix("data:").strip())

        if data_lines:
            yield from parse_openai_stream_event("\n".join(data_lines))

    return events()


def parse_openai_stream_event(data: str) -> Iterator[str]:
    if data == "[DONE]":
        return

    try:
        event = json.loads(data)
    except json.JSONDecodeError:
        return

    if event.get("type") == "response.output_text.delta":
        delta = event.get("delta")
        if isinstance(delta, str):
            yield delta

    if event.get("type") == "error":
        error = event.get("error", {})
        message = error.get("message") if isinstance(error, dict) else None
        raise RuntimeError(message or "OpenAI stream returned an error.")
