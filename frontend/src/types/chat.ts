export type Provider = "openai" | "gemini" | "anthropic";

export type ChatRole = "system" | "user" | "assistant";

export type ChatMessage = {
  role: ChatRole;
  content: string;
};

export type ChatRequest = {
  provider: Provider;
  model: string;
  apiKey?: string;
  messages: ChatMessage[];
};

export type ChatResponse = {
  message: ChatMessage;
};
