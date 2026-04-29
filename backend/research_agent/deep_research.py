#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
    from openai import APIError, OpenAI
except ImportError as exc:
    raise SystemExit(
        "Missing dependencies. Run: cd backend && source .venv/bin/activate "
        "&& pip install -r requirements.txt"
    ) from exc


BACKEND_DIR = Path(__file__).resolve().parents[1]
BACKEND_ENV_PATH = BACKEND_DIR / ".env"
OUTPUT_DIR = BACKEND_DIR / "research_agent" / "outputs"

DEFAULT_MODEL = "o4-mini-deep-research"
TERMINAL_STATUSES = {"completed", "failed", "cancelled", "expired"}
DEFAULT_TOOL_CALLS_BY_DEPTH = {
    "smoke": 3,
    "quick": 8,
    "full": None,
}


def build_equity_research_prompt(ticker: str, depth: str) -> str:
    if depth == "smoke":
        return f"""
You are a buy-side equity analyst.

Create a concise smoke-test equity research memo for {ticker.upper()}.
This is for informational and educational purposes only, not personalized
investment advice.

Keep the report under 700 words. Use only the most important current public
information. Do not attempt an exhaustive report.

Use Markdown with exactly these sections:

1. Snapshot
2. Business Quality
3. Key Financial/Valuation Signals
4. Main Risks
5. Preliminary Rating

For Preliminary Rating, choose one: Strong Buy, Buy, Hold, or Avoid.
Include a confidence score from 0 to 100.

Important:
- Prefer facts over broad narrative.
- Clearly separate facts, assumptions, and judgments.
- Use only a few high-quality sources.
- If data is uncertain or unavailable, say so instead of over-researching.
""".strip()

    if depth == "quick":
        return f"""
You are a buy-side equity analyst.

Create a quick equity research memo for {ticker.upper()} for serious individual
investors. This is for informational and educational purposes only, not
personalized investment advice.

Keep the report under 1,500 words. Use current public information, prioritizing
company filings, investor relations materials, earnings releases, and reputable
financial sources.

Use Markdown with these sections:

1. Investment Summary
2. Business Model
3. Financial/Valuation Signals
4. Catalysts
5. Risks
6. Bull / Base / Bear View
7. Preliminary Decision

For Preliminary Decision, include:
- Rating: Strong Buy, Buy, Hold, or Avoid
- Confidence score from 0 to 100
- Key assumptions
- What would make the thesis wrong

Important:
- Separate facts, assumptions, and judgments.
- Focus on what may be mispriced.
- Avoid generic descriptions.
- Use citations or source references where possible.
""".strip()

    return f"""
You are a top-tier buy-side equity analyst working at a hedge fund.

Conduct a deep equity research report on {ticker.upper()} for serious individual
investors. This is for informational and educational purposes only, not
personalized investment advice.

Use the latest public information available. Prioritize primary and high-quality
sources such as company filings, investor relations materials, earnings releases,
earnings call transcripts, reputable financial data, and credible industry
sources.

Write an institutional-style report in Markdown with these sections:

1. Investment Summary
2. Financial Analysis
3. Valuation
4. Bull / Base / Bear Scenarios
5. Final Decision

For the Final Decision, include:
- Rating: Strong Buy, Buy, Hold, or Avoid
- Confidence score from 0 to 100
- Fair value range if enough data is available

Important analytical requirements:
- Separate facts, assumptions, and judgments.
- Focus on what the market may be pricing in versus what may be mispriced.
- Avoid generic descriptions.
- Use probabilistic thinking.
- Include citations or source references where possible.
""".strip()


def response_to_dict(response: object) -> dict[str, Any]:
    if hasattr(response, "model_dump"):
        return response.model_dump(mode="json", exclude_none=True)

    if hasattr(response, "to_dict"):
        return response.to_dict()

    return {"repr": repr(response)}


def extract_output_text(response: object) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    text_parts: list[str] = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            text = getattr(content, "text", None)
            if isinstance(text, str):
                text_parts.append(text)

    return "\n\n".join(text_parts).strip()


def make_output_path(ticker: str, model: str, depth: str) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_model = model.replace("/", "_")
    return OUTPUT_DIR / f"{ticker.upper()}_{safe_model}_{depth}_{timestamp}.md"


def make_debug_path(response_id: str) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return OUTPUT_DIR / f"{response_id}_{timestamp}.debug.json"


def save_report(
    path: Path,
    ticker: str,
    model: str,
    depth: str,
    response_id: str,
    content: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    header = "\n".join(
        [
            f"# {ticker.upper()} Equity Research Report",
            "",
            f"- Model: `{model}`",
            f"- Depth: `{depth}`",
            f"- Response ID: `{response_id}`",
            f"- Generated at: `{datetime.now(timezone.utc).isoformat()}`",
            "",
            "---",
            "",
        ]
    )
    path.write_text(header + content + "\n", encoding="utf-8")


def save_debug_response(response: object) -> Path:
    response_id = getattr(response, "id", "unknown_response")
    path = make_debug_path(response_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(response_to_dict(response), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def format_failure_details(response: object) -> str:
    data = response_to_dict(response)
    fields_to_show = [
        "id",
        "status",
        "error",
        "incomplete_details",
        "last_error",
    ]

    details: dict[str, Any] = {}
    for field in fields_to_show:
        value = data.get(field)
        if value:
            details[field] = value

    if not details:
        details = data

    return json.dumps(details, indent=2, ensure_ascii=False)


def effective_max_tool_calls(depth: str, max_tool_calls: int | None) -> int | None:
    if max_tool_calls is not None:
        return max_tool_calls
    return DEFAULT_TOOL_CALLS_BY_DEPTH[depth]


def start_research(
    client: OpenAI,
    ticker: str,
    model: str,
    depth: str,
    max_tool_calls: int | None,
    use_code_interpreter: bool,
):
    tools: list[dict[str, Any]] = [{"type": "web_search_preview"}]
    if use_code_interpreter:
        tools.append({"type": "code_interpreter", "container": {"type": "auto"}})

    request_body = {
        "model": model,
        "background": True,
        "input": build_equity_research_prompt(ticker, depth),
        "tools": tools,
    }

    tool_call_limit = effective_max_tool_calls(depth, max_tool_calls)
    if tool_call_limit is not None:
        request_body["max_tool_calls"] = tool_call_limit

    return client.responses.create(**request_body)


def poll_until_done(client: OpenAI, response_id: str, poll_interval: int, timeout: int):
    started_at = time.monotonic()

    while True:
        response = client.responses.retrieve(response_id)
        status = getattr(response, "status", "unknown")
        print(f"Status: {status}")

        if status in TERMINAL_STATUSES:
            return response

        if time.monotonic() - started_at > timeout:
            raise TimeoutError(
                f"Timed out after {timeout} seconds. Response id: {response_id}"
            )

        time.sleep(poll_interval)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run or inspect a single-ticker Deep Research equity report."
    )
    parser.add_argument("--ticker", help="Ticker symbol, e.g. GOOG or BRK.B")
    parser.add_argument(
        "--response-id",
        help="Retrieve and inspect an existing Responses API response id.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        choices=["o4-mini-deep-research", "o3-deep-research"],
        help="Deep Research model to use.",
    )
    parser.add_argument(
        "--depth",
        default="smoke",
        choices=["smoke", "quick", "full"],
        help="Research depth. smoke is the lowest-token path for testing.",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=30,
        help="Seconds to wait between response status checks.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=3600,
        help="Maximum seconds to wait for the background job.",
    )
    parser.add_argument(
        "--max-tool-calls",
        type=int,
        default=None,
        help="Optional cap on tool calls. Overrides the depth default.",
    )
    parser.add_argument(
        "--use-code-interpreter",
        action="store_true",
        help="Enable code_interpreter. Disabled by default to reduce token usage.",
    )
    args = parser.parse_args()

    if not args.ticker and not args.response_id:
        parser.error("one of --ticker or --response-id is required")

    return args


def get_openai_api_key() -> str:
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing OpenAI API key. Set OPENAI_API_KEY or OPENAI_KEY in backend/.env."
        )
    return api_key


def handle_final_response(response: object, ticker: str | None, model: str, depth: str) -> int:
    status = getattr(response, "status", "unknown")
    if status != "completed":
        print(f"Research did not complete successfully. Final status: {status}")
        print("Failure details:")
        print(format_failure_details(response))
        debug_path = save_debug_response(response)
        print(f"Saved debug response: {debug_path}")
        return 1

    report = extract_output_text(response)
    if not report:
        print("Research completed, but no report text was found in the response.")
        debug_path = save_debug_response(response)
        print(f"Saved debug response: {debug_path}")
        return 1

    output_path = make_output_path(ticker or "UNKNOWN", model, depth)
    save_report(
        path=output_path,
        ticker=ticker or "UNKNOWN",
        model=model,
        depth=depth,
        response_id=getattr(response, "id", "unknown_response"),
        content=report,
    )

    print(f"Saved report: {output_path}")
    return 0


def main() -> int:
    args = parse_args()
    load_dotenv(BACKEND_ENV_PATH)

    client = OpenAI(api_key=get_openai_api_key(), timeout=3600)

    try:
        if args.response_id:
            print(f"Retrieving response: {args.response_id}")
            response = client.responses.retrieve(args.response_id)
            print(f"Status: {getattr(response, 'status', 'unknown')}")
            return handle_final_response(response, args.ticker, args.model, args.depth)

        ticker = args.ticker.upper()
        print(f"Starting Deep Research for {ticker} with {args.model}...")
        print(f"Depth: {args.depth}")
        print(f"Max tool calls: {effective_max_tool_calls(args.depth, args.max_tool_calls)}")
        print(f"Code interpreter: {'enabled' if args.use_code_interpreter else 'disabled'}")
        initial_response = start_research(
            client=client,
            ticker=ticker,
            model=args.model,
            depth=args.depth,
            max_tool_calls=args.max_tool_calls,
            use_code_interpreter=args.use_code_interpreter,
        )
        response_id = initial_response.id
        print(f"Response ID: {response_id}")

        final_response = poll_until_done(
            client=client,
            response_id=response_id,
            poll_interval=args.poll_interval,
            timeout=args.timeout,
        )
    except APIError as exc:
        print(f"OpenAI API request failed: {exc.__class__.__name__}: {exc}")
        return 1

    return handle_final_response(final_response, ticker, args.model, args.depth)


if __name__ == "__main__":
    raise SystemExit(main())
