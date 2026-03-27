"""Response generation service with optional external model support."""

from __future__ import annotations

import os
from typing import List

import httpx
from fastapi import HTTPException

from backend.app.schemas import MemoryItem


class LLMService:
    """Generate assistant replies using either an API or a local fallback.

    The service is configured to work well with OpenRouter by default while
    still supporting any OpenAI-compatible chat completion endpoint.
    """

    def __init__(self) -> None:
        """Load runtime configuration from environment variables.

        Environment variables:
            OPENAI_API_KEY: Primary API key variable for OpenAI-compatible usage.
            OPENROUTER_API_KEY: Alternate API key variable for OpenRouter usage.
            OPENAI_BASE_URL: Base URL for the provider chat completions endpoint.
            OPENAI_MODEL: Model identifier used for chat completions.
        """

        self.api_key = (
            os.getenv("OPENROUTER_API_KEY", "").strip()
            or os.getenv("OPENAI_API_KEY", "").strip()
        )
        self.base_url = os.getenv(
            "OPENAI_BASE_URL",
            "https://openrouter.ai/api/v1",
        ).strip()
        self.model = os.getenv("OPENAI_MODEL", "openai/gpt-4o-mini").strip()
        self.temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))
        self.fallback_model = os.getenv(
            "OPENAI_FALLBACK_MODEL",
            "openai/gpt-4o-mini",
        ).strip()

    async def generate_reply(
        self,
        system_prompt: str,
        user_message: str,
        recent_memory: List[MemoryItem],
        summary: str,
        context_tags: List[str],
        guardrail_notes: List[str],
    ) -> str:
        """Generate an assistant response grounded in memory and session context.

        Args:
            system_prompt: Stable assistant instruction block.
            user_message: Latest user message after sanitization.
            recent_memory: Remembered messages used for continuity.
            summary: Prompt-friendly session summary text.
            context_tags: Current high-level topic labels.
            guardrail_notes: Notes describing any safety-related handling.

        Returns:
            str: Assistant response content for the frontend.
        """

        if self.api_key:
            return await self._generate_api_reply(
                system_prompt=system_prompt,
                user_message=user_message,
                recent_memory=recent_memory,
                summary=summary,
                context_tags=context_tags,
                guardrail_notes=guardrail_notes,
            )

        return self._generate_local_reply(
            user_message=user_message,
            recent_memory=recent_memory,
            summary=summary,
            context_tags=context_tags,
            guardrail_notes=guardrail_notes,
        )

    async def _generate_api_reply(
        self,
        system_prompt: str,
        user_message: str,
        recent_memory: List[MemoryItem],
        summary: str,
        context_tags: List[str],
        guardrail_notes: List[str],
    ) -> str:
        """Call an OpenAI-compatible chat completion endpoint.

        This request includes OpenRouter-friendly headers while remaining valid
        for other compatible providers.
        """

        memory_text = "\n".join(
            f"{message.role}: {message.content}" for message in recent_memory
        ) or "No recent memory."
        guardrail_text = (
            "; ".join(guardrail_notes) if guardrail_notes else "No special guardrail actions."
        )
        context_text = ", ".join(context_tags) if context_tags else "general"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "http://127.0.0.1:8000"),
            "X-Title": os.getenv("OPENROUTER_APP_NAME", "Context Tracking Memory Agent"),
        }

        models_to_try = [self.model]
        if self.fallback_model and self.fallback_model not in models_to_try:
            models_to_try.append(self.fallback_model)

        last_error_message = "Unknown model provider error."

        async with httpx.AsyncClient(timeout=30.0) as client:
            for model_name in models_to_try:
                payload = {
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "system",
                            "content": (
                                f"Conversation summary: {summary}\n"
                                f"Context tags: {context_text}\n"
                                f"Guardrail notes: {guardrail_text}\n"
                                f"Recent memory:\n{memory_text}"
                            ),
                        },
                        {"role": "user", "content": user_message},
                    ],
                    "temperature": self.temperature,
                }

                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )

                if response.is_success:
                    data = response.json()
                    return data["choices"][0]["message"]["content"].strip()

                provider_message = self._extract_provider_error(response)
                last_error_message = (
                    f"Model `{model_name}` failed with status {response.status_code}: {provider_message}"
                )

                if response.status_code < 500 and model_name == models_to_try[-1]:
                    break

        raise HTTPException(status_code=502, detail=last_error_message)

    def _extract_provider_error(self, response: httpx.Response) -> str:
        """Extract a readable error message from a provider HTTP response.

        Args:
            response: HTTP response returned by the upstream model provider.

        Returns:
            str: Concise provider error text for debugging and frontend display.
        """

        try:
            payload = response.json()
        except ValueError:
            return response.text.strip() or "No response body was returned."

        if isinstance(payload, dict):
            error_block = payload.get("error")
            if isinstance(error_block, dict):
                return str(error_block.get("message") or error_block)
            if error_block:
                return str(error_block)
            message = payload.get("message")
            if message:
                return str(message)

        return str(payload)

    def _generate_local_reply(
        self,
        user_message: str,
        recent_memory: List[MemoryItem],
        summary: str,
        context_tags: List[str],
        guardrail_notes: List[str],
    ) -> str:
        """Return a deterministic fallback response when no API key is set."""

        previous_user_messages = [
            message.content for message in recent_memory[:-1] if message.role == "user"
        ]
        memory_reference = (
            previous_user_messages[-1]
            if previous_user_messages
            else "this is the first interaction in the tracked memory window"
        )
        topics = ", ".join(context_tags) if context_tags else "general topics"
        guardrail_prefix = (
            "I noticed an unsafe instruction pattern and ignored it. "
            if guardrail_notes
            else ""
        )

        return (
            f"{guardrail_prefix}You said: \"{user_message}\". "
            f"I am tracking the recent conversation and currently remember that one earlier focus was \"{memory_reference}\". "
            f"My active context tags are: {topics}. "
            f"Session summary: {summary}"
        )
