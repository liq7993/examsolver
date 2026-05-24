"""Shared LLM Protocols and message contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class Message:
    """One chat message passed to an LLM client."""

    role: Literal["system", "user", "assistant"]
    content: str
    images: list[bytes] = field(default_factory=list)


@runtime_checkable
class LLMClient(Protocol):
    """Protocol implemented by cloud and local LLM clients."""

    def chat(
        self,
        messages: list[Message],
        *,
        json_schema: dict[str, object] | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
        timeout: float = 30.0,
    ) -> str:
        """Return a text response for a chat request."""

    def chat_with_image(
        self,
        messages: list[Message],
        images: list[bytes],
        **kwargs: object,
    ) -> str:
        """Return a text response for a multimodal chat request."""
