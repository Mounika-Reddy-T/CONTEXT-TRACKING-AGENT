"""FastAPI entrypoint for the context tracking memory agent project."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from backend.app.schemas import ChatRequest, ChatResponse, SessionSnapshotResponse
from backend.app.services.guardrails import apply_input_guardrails, build_system_prompt
from backend.app.services.llm import LLMService
from backend.app.services.memory import MemoryStore


BASE_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = BASE_DIR / "frontend"

# Load environment variables from the project root before services are created.
load_dotenv(BASE_DIR / ".env")

app = FastAPI(
    title="Context Tracking Memory Agent",
    description="A FastAPI app with short-term memory, context tracking, and prompt guardrails.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=FRONTEND_DIR / "static"), name="static")

memory_store = MemoryStore(interaction_window=3)
llm_service = LLMService()


@app.get("/", response_class=FileResponse)
async def serve_homepage() -> FileResponse:
    """Serve the single-page frontend for the memory agent application."""

    index_file = FRONTEND_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Frontend index.html was not found.")
    return FileResponse(index_file)


@app.get("/favicon.ico")
async def favicon() -> Response:
    """Return an empty favicon response to avoid browser 404 noise.

    Returns:
        Response: Empty 204 response for browsers requesting `/favicon.ico`.
    """

    return Response(status_code=204)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Process one chat turn and update session memory."""

    guardrail_result = apply_input_guardrails(request.message)
    system_prompt = build_system_prompt()

    memory_store.add_message(
        session_id=request.session_id,
        role="user",
        content=guardrail_result.sanitized_message,
    )

    recent_memory = memory_store.get_recent_memory(request.session_id)
    summary = memory_store.get_summary(request.session_id)
    context_tags = memory_store.get_context_tags(request.session_id)

    assistant_response = await llm_service.generate_reply(
        system_prompt=system_prompt,
        user_message=guardrail_result.sanitized_message,
        recent_memory=recent_memory,
        summary=summary,
        context_tags=context_tags,
        guardrail_notes=guardrail_result.notes,
    )

    memory_store.add_message(
        session_id=request.session_id,
        role="assistant",
        content=assistant_response,
    )

    return ChatResponse(
        response=assistant_response,
        session_id=request.session_id,
        recent_memory=memory_store.get_recent_memory(request.session_id),
        context_tags=memory_store.get_context_tags(request.session_id),
        guardrail_notes=guardrail_result.notes,
    )


@app.get("/api/session/{session_id}", response_model=SessionSnapshotResponse)
async def get_session_snapshot(session_id: str) -> SessionSnapshotResponse:
    """Return the current memory snapshot for a session identifier."""

    return SessionSnapshotResponse(
        session_id=session_id,
        recent_memory=memory_store.get_recent_memory(session_id),
        context_tags=memory_store.get_context_tags(session_id),
        total_messages=memory_store.get_total_messages(session_id),
        summary=memory_store.get_summary(session_id),
    )
