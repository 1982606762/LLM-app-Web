import json
import os
from pathlib import Path
from typing import Any

from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .providers.anthropic import call_anthropic
from .providers.gemini import call_gemini
from .providers.openai import call_openai


PROVIDERS = {
    "openai": call_openai,
    "gemini": call_gemini,
    "anthropic": call_anthropic,
}

PROVIDER_ENV_KEYS = {
    "openai": ["OPENAI_API_KEY", "OPENAI_KEY"],
    "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
    "anthropic": ["ANTHROPIC_API_KEY", "CLAUDE_API_KEY"],
}

ALLOWED_ORIGINS = {
    "http://localhost:5173",
    "http://127.0.0.1:5173",
}


def load_local_env() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def get_provider_api_key(provider: str, api_key_from_request: str | None) -> str | None:
    if api_key_from_request:
        return api_key_from_request

    for env_key in PROVIDER_ENV_KEYS.get(provider, []):
        value = os.environ.get(env_key)
        if value:
            return value

    return None


load_local_env()


def with_cors(response: JsonResponse, request: HttpRequest | None = None) -> JsonResponse:
    origin = request.headers.get("Origin") if request else None
    response["Access-Control-Allow-Origin"] = origin if origin in ALLOWED_ORIGINS else "http://127.0.0.1:5173"
    response["Access-Control-Allow-Headers"] = "Content-Type"
    response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    return response


def error_response(message: str, status: int = 400, request: HttpRequest | None = None) -> JsonResponse:
    return with_cors(JsonResponse({"error": message}, status=status), request)


@csrf_exempt
def chat_view(request: HttpRequest) -> JsonResponse:
    if request.method == "OPTIONS":
        return with_cors(JsonResponse({}), request)

    if request.method != "POST":
        return error_response("Only POST is supported.", status=405, request=request)

    try:
        payload: dict[str, Any] = json.loads(request.body)
    except json.JSONDecodeError:
        return error_response("Request body must be valid JSON.", request=request)

    provider = payload.get("provider")
    model = payload.get("model")
    api_key = get_provider_api_key(provider, payload.get("apiKey"))
    messages = payload.get("messages")

    if provider not in PROVIDERS:
        return error_response("Unsupported provider.", request=request)
    if not model:
        return error_response("Model is required.", request=request)
    if not api_key:
        env_names = ", ".join(PROVIDER_ENV_KEYS.get(provider, []))
        return error_response(
            f"API key is required. Enter it in the UI or set one of these in backend/.env: {env_names}.",
            request=request,
        )
    if not isinstance(messages, list) or not messages:
        return error_response("Messages must be a non-empty list.", request=request)

    try:
        content = PROVIDERS[provider](api_key=api_key, model=model, messages=messages)
    except Exception as exc:
        return error_response(str(exc), status=502, request=request)

    return with_cors(JsonResponse({"message": {"role": "assistant", "content": content}}), request)
