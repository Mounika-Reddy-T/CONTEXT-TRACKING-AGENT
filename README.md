# Context Tracking Agent

A FastAPI-based conversational agent with short-term memory, context tracking, prompt guardrails, and an OpenRouter-powered LLM backend.

## Features

- **Session Memory** — remembers the last 3 user-assistant interaction pairs per session
- **Context Tags** — automatically extracts topic keywords from user messages
- **Session Summary** — builds a compact summary grounded in recent memory
- **Prompt Guardrails** — detects and neutralizes prompt-injection attempts
- **LLM Integration** — uses OpenRouter (OpenAI-compatible) with a configurable fallback model
- **Single-page Frontend** — chat UI with a live memory inspector panel

## Project Structure

```
context_tracking_agent/
├── backend/
│   └── app/
│       ├── main.py          # FastAPI app, routes
│       ├── schemas.py       # Pydantic request/response models
│       └── services/
│           ├── llm.py       # LLM API integration
│           ├── memory.py    # In-memory session store
│           └── guardrails.py# Input sanitization & prompt hardening
├── frontend/
│   ├── index.html
│   └── static/
│       ├── app.js
│       └── styles.css
├── .env
├── .gitignore
└── requirements.txt
```

## Setup

1. **Clone the repo**
   ```bash
   git clone https://github.com/Mounika-Reddy-T/CONTEXT-TRACKING-AGENT.git
   cd CONTEXT-TRACKING-AGENT
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate      # Windows
   source venv/bin/activate   # macOS/Linux
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables** — create a `.env` file in the project root:
   ```env
   OPENROUTER_API_KEY=<your_openrouter_api_key>
   OPENAI_BASE_URL=https://openrouter.ai/api/v1
   OPENAI_MODEL=openai/gpt-4o-mini
   OPENAI_TEMPERATURE=0.2
   OPENAI_FALLBACK_MODEL=openai/gpt-4o-mini
   OPENROUTER_SITE_URL=http://127.0.0.1:8000
   OPENROUTER_APP_NAME=Context Tracking Memory Agent
   ```

5. **Run the server**
   ```bash
   uvicorn backend.app.main:app --reload
   ```

6. Open `http://127.0.0.1:8000` in your browser.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Serves the frontend UI |
| `POST` | `/api/chat` | Send a message and get a response |
| `GET` | `/api/session/{session_id}` | Inspect current session memory snapshot |

### POST `/api/chat`

**Request**
```json
{
  "message": "What is machine learning?",
  "session_id": "user-123"
}
```

**Response**
```json
{
  "response": "Machine learning is...",
  "session_id": "user-123",
  "recent_memory": [...],
  "context_tags": ["machine", "learning"],
  "guardrail_notes": []
}
```

## Tech Stack

- [FastAPI](https://fastapi.tiangolo.com/)
- [Uvicorn](https://www.uvicorn.org/)
- [Pydantic v2](https://docs.pydantic.dev/)
- [HTTPX](https://www.python-httpx.org/)
- [OpenRouter](https://openrouter.ai/)
