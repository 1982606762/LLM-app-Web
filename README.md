# Personal LLM Client

This is a learning project for building your own multi-provider LLM chat client.

The first milestone is intentionally small:

- React + TypeScript frontend
- Django backend
- One unified `/api/chat/` endpoint
- Provider adapters for OpenAI, Gemini, and Anthropic Claude
- API keys are provided per request for local learning only

## Project Layout

```text
backend/
  manage.py
  llm_client/
    settings.py
    urls.py
  chat/
    views.py
    providers/
      openai.py
      gemini.py
      anthropic.py

frontend/
  src/
    App.tsx
    api/chat.ts
    types/chat.ts
```

## Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py runserver 8000
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Then open the Vite URL, usually `http://localhost:5173`.

## Learning Notes

The frontend only knows one API shape:

```ts
{
  provider: "openai" | "gemini" | "anthropic",
  model: string,
  apiKey: string,
  messages: [{ role: "user", content: "Hello" }]
}
```

The backend converts that single shape into the different API formats each provider expects. This is called the adapter pattern.
