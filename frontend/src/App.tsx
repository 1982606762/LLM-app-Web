import { FormEvent, useState } from "react";
import { sendChatMessage } from "./api/chat";
import type { ChatMessage, Provider } from "./types/chat";

const DEFAULT_MODELS: Record<Provider, string> = {
  openai: "gpt-5.4-mini",
  gemini: "gemini-2.5-flash",
  anthropic: "claude-sonnet-4-5",
};

const PROVIDER_LABELS: Record<Provider, string> = {
  openai: "OpenAI",
  gemini: "Gemini",
  anthropic: "Claude",
};

function App() {
  const [provider, setProvider] = useState<Provider>("openai");
  const [model, setModel] = useState(DEFAULT_MODELS.openai);
  const [apiKey, setApiKey] = useState("");
  const [input, setInput] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("You are a helpful assistant.");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleProviderChange(nextProvider: Provider) {
    setProvider(nextProvider);
    setModel(DEFAULT_MODELS[nextProvider]);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const trimmedInput = input.trim();
    if (!trimmedInput || isLoading) {
      return;
    }

    const userMessage: ChatMessage = { role: "user", content: trimmedInput };
    const nextMessages = [...messages, userMessage];

    setMessages(nextMessages);
    setInput("");
    setError(null);
    setIsLoading(true);

    try {
      const response = await sendChatMessage({
        provider,
        model,
        apiKey,
        messages: [
          ...(systemPrompt.trim()
            ? [{ role: "system" as const, content: systemPrompt.trim() }]
            : []),
          ...nextMessages,
        ],
      });
      setMessages([...nextMessages, response.message]);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unknown error.");
      setMessages(messages);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="app-shell">
      <aside className="settings-panel">
        <div className="brand-block">
          <span className="brand-mark">LLM</span>
          <div>
            <p className="eyebrow">Personal Client</p>
            <h1>多模型聊天</h1>
          </div>
        </div>

        <div className="settings-section">
          <label>
            Provider
            <select
              value={provider}
              onChange={(event) => handleProviderChange(event.target.value as Provider)}
            >
              {Object.entries(PROVIDER_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>

          <label>
            Model
            <input value={model} onChange={(event) => setModel(event.target.value)} />
          </label>

          <label>
            API Key Override
            <input
              value={apiKey}
              onChange={(event) => setApiKey(event.target.value)}
              placeholder="Optional when backend/.env is set"
              type="password"
            />
          </label>
        </div>

        <div className="settings-section prompt-section">
          <label>
            System Prompt
            <textarea
              value={systemPrompt}
              onChange={(event) => setSystemPrompt(event.target.value)}
              rows={6}
            />
          </label>
        </div>

        <div className="lesson-box">
          <strong>这一步你在学什么</strong>
          <span>
            前端只发送统一格式，Django 后端把它转换成不同模型厂商需要的格式。
          </span>
        </div>
      </aside>

      <section className="chat-panel">
        <div className="chat-header">
          <div>
            <p className="eyebrow">{PROVIDER_LABELS[provider]}</p>
            <h2>{model}</h2>
          </div>
          <div className="header-actions">
            <span className="message-count">{messages.length} messages</span>
            <span className={`status ${isLoading ? "loading" : ""}`}>
              {isLoading ? "Thinking" : "Ready"}
            </span>
          </div>
        </div>

        <div className="messages" aria-live="polite">
          {messages.length === 0 ? (
            <div className="empty-state">
              <h2>开始你的第一轮对话</h2>
              <p>选择模型，然后发送一条消息。</p>
            </div>
          ) : (
            messages.map((message, index) => (
              <article className={`message ${message.role}`} key={`${message.role}-${index}`}>
                <span>{message.role}</span>
                <p>{message.content}</p>
              </article>
            ))
          )}
        </div>

        {error ? <div className="error-banner">{error}</div> : null}

        <form className="composer" onSubmit={handleSubmit}>
          <div className="composer-box">
            <textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="输入消息..."
              rows={3}
            />
            <button disabled={!input.trim() || isLoading} type="submit">
              Send
            </button>
          </div>
        </form>
      </section>
    </main>
  );
}

export default App;
