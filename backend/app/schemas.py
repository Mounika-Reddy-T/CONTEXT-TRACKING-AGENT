"""Pydantic schemas used by the FastAPI application."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Represent a chat request submitted by the frontend client.

    Attributes:
        message: The latest user message that should be processed.
        session_id: The logical conversation identifier for memory lookup.
    """

    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str = Field(..., min_length=1, max_length=100)


class MemoryItem(BaseModel):
    """Represent one stored interaction for frontend rendering.

    Attributes:
        role: The actor who produced the message.
        content: The text content for the stored message.
        created_at: ISO timestamp describing when the message was stored.
    """

    role: str
    content: str
    created_at: str


class ChatResponse(BaseModel):
    """Return the agent answer plus memory diagnostics to the frontend.

    Attributes:
        response: Final assistant reply returned to the UI.
        session_id: The conversation identifier used for this turn.
        recent_memory: The last remembered interactions tracked by the agent.
        context_tags: Lightweight topic labels extracted from the session.
        guardrail_notes: Information about any guardrail decisions taken.
    """

    response: str
    session_id: str
    recent_memory: List[MemoryItem]
    context_tags: List[str]
    guardrail_notes: List[str]


class SessionSnapshotResponse(BaseModel):
    """Expose the current in-memory session state for quick inspection.

    Attributes:
        session_id: The conversation identifier requested by the client.
        recent_memory: The most recent stored interactions for the session.
        context_tags: Current extracted session topic labels.
        total_messages: Total number of stored messages in the session.
        summary: Short generated session summary used for grounding.
    """

    session_id: str
    recent_memory: List[MemoryItem]
    context_tags: List[str]
    total_messages: int
    summary: Optional[str]
