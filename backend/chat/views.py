import json
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


def with_cors(response: JsonResponse) -> JsonResponse:
    response["Access-Control-Allow-Origin"] = "http://localhost:5173"
    response["Access-Control-Allow-Headers"] = "Content-Type"
    response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    return response


def error_response(message: str, status: int = 400) -> JsonResponse:
    return with_cors(JsonResponse({"error": message}, status=status))


@csrf_exempt
def chat_view(request: HttpRequest) -> JsonResponse:
    if request.method == "OPTIONS":
        return with_cors(JsonResponse({}))

    if request.method != "POST":
        return error_response("Only POST is supported.", status=405)

    try:
        payload: dict[str, Any] = json.loads(request.body)
    except json.JSONDecodeError:
        return error_response("Request body must be valid JSON.")

    provider = payload.get("provider")
    model = payload.get("model")
    api_key = payload.get("apiKey")
    messages = payload.get("messages")

    if provider not in PROVIDERS:
        return error_response("Unsupported provider.")
    if not model:
        return error_response("Model is required.")
    if not api_key:
        return error_response("API key is required.")
    if not isinstance(messages, list) or not messages:
        return error_response("Messages must be a non-empty list.")

    try:
        content = PROVIDERS[provider](api_key=api_key, model=model, messages=messages)
    except Exception as exc:
        return error_response(str(exc), status=502)

    return with_cors(JsonResponse({"message": {"role": "assistant", "content": content}}))
