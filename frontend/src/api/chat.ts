import type { ChatRequest, ChatResponse } from "../types/chat";

const API_BASE_URL = "http://127.0.0.1:8000/api";

export async function sendChatMessage(request: ChatRequest): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/chat/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error ?? "Chat request failed.");
  }

  return data;
}
