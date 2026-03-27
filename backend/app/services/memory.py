"""In-memory storage and context tracking helpers for chat sessions."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List

from backend.app.schemas import MemoryItem


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "me",
    "my",
    "of",
    "on",
    "or",
    "please",
    "the",
    "this",
    "to",
    "we",
    "with",
    "you",
    "your",
}


@dataclass
class SessionMemory:
    """Maintain short-term memory and derived context for one session.

    Attributes:
        messages: Stored conversation turns for the session.
        summary: Short textual summary of the latest conversation state.
        context_tags: Extracted topic labels used for UI display and prompting.
    """

    messages: List[MemoryItem] = field(default_factory=list)
    summary: str = ""
    context_tags: List[str] = field(default_factory=list)


class MemoryStore:
    """Store all sessions in process memory for the FastAPI application."""

    def __init__(self, interaction_window: int = 3) -> None:
        """Initialize the store with a fixed interaction memory window.

        Args:
            interaction_window: Number of user-assistant pairs to remember.
        """

        self._sessions: Dict[str, SessionMemory] = defaultdict(SessionMemory)
        self._interaction_window = interaction_window

    def add_message(self, session_id: str, role: str, content: str) -> None:
        """Append a message to a session and refresh derived context.

        Args:
            session_id: Conversation identifier supplied by the frontend.
            role: Message role, typically `user` or `assistant`.
            content: Text content to store in the session.
        """

        timestamp = datetime.now(timezone.utc).isoformat()
        self._sessions[session_id].messages.append(
            MemoryItem(role=role, content=content, created_at=timestamp)
        )
        self._refresh_context(session_id)

    def get_recent_memory(self, session_id: str) -> List[MemoryItem]:
        """Return the last remembered interactions for a given session."""

        window_size = self._interaction_window * 2
        return self._sessions[session_id].messages[-window_size:]

    def get_summary(self, session_id: str) -> str:
        """Return the latest generated summary for the selected session."""

        return self._sessions[session_id].summary

    def get_context_tags(self, session_id: str) -> List[str]:
        """Return current topic tags for a session."""

        return self._sessions[session_id].context_tags

    def get_total_messages(self, session_id: str) -> int:
        """Return how many messages are stored for the session."""

        return len(self._sessions[session_id].messages)

    def _refresh_context(self, session_id: str) -> None:
        """Recompute summary and topic tags after each new message."""

        session = self._sessions[session_id]
        recent_messages = self.get_recent_memory(session_id)
        user_messages = [
            message.content for message in session.messages if message.role == "user"
        ]

        session.context_tags = self._extract_context_tags(user_messages)
        session.summary = self._build_summary(recent_messages, session.context_tags)

    def _extract_context_tags(self, messages: List[str]) -> List[str]:
        """Extract simple topic tags from user messages using token counts."""

        counter: Counter[str] = Counter()

        for message in messages:
            for token in message.lower().split():
                cleaned_token = "".join(
                    character for character in token if character.isalnum()
                )
                if len(cleaned_token) < 3 or cleaned_token in STOPWORDS:
                    continue
                counter[cleaned_token] += 1

        return [token for token, _ in counter.most_common(5)]

    def _build_summary(self, messages: List[MemoryItem], context_tags: List[str]) -> str:
        """Create a compact summary string from recent memory and topics."""

        if not messages:
            return "No conversation history is available yet."

        latest_user_message = next(
            (message.content for message in reversed(messages) if message.role == "user"),
            "No user message found.",
        )
        tag_summary = ", ".join(context_tags) if context_tags else "general conversation"
        return (
            f"Latest user focus: {latest_user_message[:180]}. "
            f"Tracked topics: {tag_summary}."
        )
