"""Fake LLM client for deterministic tests."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from typing import cast

from examsolver.llm.base import Message


@dataclass(frozen=True, slots=True)
class _RecordedResponse:
    prompt_contains: str
    response: str


class FakeLLMClient:
    """In-memory LLMClient test double with prompt substring matching."""

    def __init__(
        self,
        *,
        task_kind: str = "unknown",
        default_response: str | None = None,
        recorded: Mapping[tuple[str, str], str] | None = None,
    ) -> None:
        self.task_kind = task_kind
        self.call_count = 0
        self.last_messages: list[Message] | None = None
        self.last_json_schema: dict[str, object] | None = None
        self.recorded: dict[tuple[str, str], str] = dict(recorded or {})
        self._default_response = default_response
        self._records: list[_RecordedResponse] = []

    @classmethod
    def from_recorded(cls, payload: str | dict[str, object]) -> "FakeLLMClient":
        """Return a fake that answers every unmatched chat with one recorded payload."""

        if isinstance(payload, str):
            response = payload
        else:
            response = json.dumps(payload, ensure_ascii=False)
        return cls(default_response=response)

    @classmethod
    def always(cls, response: str) -> "FakeLLMClient":
        """Return a fake that always answers with the same string."""

        return cls.from_recorded(response)

    def record(self, *, prompt_contains: str, response: str) -> None:
        """Register a response returned when the last user prompt contains a substring."""

        self._records.append(_RecordedResponse(prompt_contains=prompt_contains, response=response))

    def record_hash(
        self,
        *,
        prompt_hash: str,
        response: str,
        task_kind: str | None = None,
    ) -> None:
        """Register a response by ``(task_kind, prompt_hash)``."""

        self.recorded[(task_kind or self.task_kind, prompt_hash)] = response

    def chat(
        self,
        messages: list[Message],
        *,
        json_schema: dict[str, object] | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
        timeout: float = 30.0,
        **kwargs: object,
    ) -> str:
        """Return a matching recorded response or fail loudly for unexpected prompts."""

        _ = (max_tokens, temperature, timeout, kwargs)
        self.call_count += 1
        self.last_messages = messages
        self.last_json_schema = json_schema

        content = _last_user_content(messages)
        for record in self._records:
            if record.prompt_contains in content:
                return record.response
        recorded_response = self.recorded.get((self.task_kind, prompt_hash(content)))
        if recorded_response is not None:
            return recorded_response
        if self._default_response is not None:
            return self._default_response
        raise AssertionError(f"FakeLLM: unexpected prompt: {content[:200]}")

    def chat_with_image(
        self,
        messages: list[Message],
        images: list[bytes],
        **kwargs: object,
    ) -> str:
        """Return the same fake chat response while accepting image inputs."""

        _ = images
        json_schema = kwargs.get("json_schema")
        if json_schema is not None and not isinstance(json_schema, dict):
            raise TypeError("json_schema must be a dict")
        return self.chat(
            messages,
            json_schema=cast(dict[str, object] | None, json_schema),
            max_tokens=_int_kwarg(kwargs, "max_tokens", 1024),
            temperature=_float_kwarg(kwargs, "temperature", 0.2),
            timeout=_float_kwarg(kwargs, "timeout", 30.0),
        )


def _last_user_content(messages: list[Message]) -> str:
    for message in reversed(messages):
        if message.role == "user":
            return message.content
    return ""


def prompt_hash(content: str) -> str:
    """Return the stable prompt hash used by FakeLLMClient recordings."""

    return sha256(content.encode("utf-8")).hexdigest()


def _int_kwarg(kwargs: Mapping[str, object], name: str, default: int) -> int:
    value = kwargs.get(name, default)
    if isinstance(value, int):
        return value
    raise TypeError(f"{name} must be an int")


def _float_kwarg(kwargs: Mapping[str, object], name: str, default: float) -> float:
    value = kwargs.get(name, default)
    if isinstance(value, int | float):
        return float(value)
    raise TypeError(f"{name} must be a float")
