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

## Equity Research Agent: Phase 1

The first equity-research milestone is a CLI that runs one Deep Research job for
one ticker and saves the finished report as Markdown.

Install backend dependencies:

```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt
```

Make sure `backend/.env` contains either:

```text
OPENAI_API_KEY=...
```

or:

```text
OPENAI_KEY=...
```

Run:

```bash
python research_agent/deep_research.py --ticker GOOG --model o4-mini-deep-research --depth smoke
```

The command starts a background Deep Research response, polls until completion,
and saves the report into `backend/research_agent/outputs/`.

Depth options:

```text
smoke  -> lowest-token test path, short memo, default max_tool_calls=3
quick  -> medium memo, default max_tool_calls=8
full   -> longer report, no default tool-call cap
```

By default the CLI only uses `web_search_preview`. Add code execution only when
you need it:

```bash
python research_agent/deep_research.py --ticker GOOG --depth quick --use-code-interpreter
```

If a response fails, inspect the error details for an existing response:

```bash
python research_agent/deep_research.py --response-id resp_...
```

Useful learning points in this step:

- `argparse` turns command-line flags into Python values.
- `.env` keeps secrets out of source code.
- `background=True` is used because Deep Research can take minutes.
- `web_search_preview` gives the model a public-web data source.
- `code_interpreter` can be enabled for calculations, but is off by default to reduce token usage.
- Saving Markdown gives us a concrete artifact before adding database/UI layers.
