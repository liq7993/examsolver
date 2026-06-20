"""OpenAI-compatible ``/chat/completions`` client.

A single synchronous client for any server speaking the OpenAI chat-completions
wire format. It backs both the local llama-server
(:class:`~examsolver.llm.local_gguf.LocalGGUFClient`, no API key) and hosted
cloud providers (DeepSeek, Moonshot, OpenAI, ...) which authenticate with a
``Bearer`` token. The request shape, retry policy, and logging are identical
across backends, so they live here once.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, cast

import httpx

from examsolver.llm.base import Message

logger = logging.getLogger(__name__)


class OpenAICompatibleClient:
    """Synchronous OpenAI-compatible chat client.

    ``api_key`` is optional: a local llama-server needs none, while cloud
    providers send it as a ``Bearer`` token. ``provider_label`` only colours
    log lines so each backend stays distinguishable in the logs.
    """

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str | None = None,
        task_kind: str = "unknown",
        provider_label: str = "openai_compatible",
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._api_key = api_key
        self.task_kind = task_kind
        self.provider_label = provider_label
        self._client = client or httpx.Client()

    def chat(
        self,
        messages: list[Message],
        *,
        json_schema: dict[str, object] | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
        timeout: float = 30.0,
    ) -> str:
        """Return the first OpenAI-compatible chat completion message content."""

        payload: dict[str, object] = {
            "model": self.model,
            "messages": _messages_payload(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if json_schema is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "structured_output",
                    "schema": json_schema,
                    "strict": True,
                },
            }

        data = self._post(payload, timeout=timeout)
        return _message_content(data)

    def chat_with_image(
        self,
        messages: list[Message],
        images: list[bytes],
        **kwargs: object,
    ) -> str:
        """OpenAI-compatible text clients do not provide VLM support in M2."""

        _ = (messages, images, kwargs)
        raise NotImplementedError(f"{type(self).__name__} does not support image input")

    def _headers(self) -> dict[str, str]:
        if self._api_key:
            return {"Authorization": f"Bearer {self._api_key}"}
        return {}

    def _post(self, payload: dict[str, object], *, timeout: float) -> dict[str, Any]:
        started = time.perf_counter()
        logger.info(
            "[unknown] INFO llm.%s.chat: begin task_kind=%s model=%s",
            self.provider_label,
            self.task_kind,
            self.model,
        )
        response = self._post_with_retry(payload, timeout=timeout)
        latency = time.perf_counter() - started
        data = response.json()
        usage = data.get("usage") if isinstance(data, dict) else {}
        tokens_in = usage.get("prompt_tokens", 0) if isinstance(usage, dict) else 0
        tokens_out = usage.get("completion_tokens", 0) if isinstance(usage, dict) else 0
        logger.info(
            "[unknown] INFO llm.%s.chat: done task_kind=%s tokens_in=%s "
            "tokens_out=%s latency=%.2fs",
            self.provider_label,
            self.task_kind,
            tokens_in,
            tokens_out,
            latency,
        )
        return cast(dict[str, Any], data)

    def _post_with_retry(self, payload: dict[str, object], *, timeout: float) -> httpx.Response:
        headers = self._headers()
        last_error: httpx.RequestError | httpx.HTTPStatusError | None = None
        for attempt in range(2):
            try:
                response = self._client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=timeout,
                )
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code < 500:
                    raise
                last_error = exc
            except httpx.RequestError as exc:
                last_error = exc
            if attempt == 0:
                logger.warning(
                    "[unknown] WARNING llm.%s.chat: retry task_kind=%s",
                    self.provider_label,
                    self.task_kind,
                )
        if last_error is None:
            raise RuntimeError("OpenAI-compatible request failed without an exception")
        raise last_error


def _messages_payload(messages: list[Message]) -> list[dict[str, str]]:
    return [{"role": message.role, "content": message.content} for message in messages]


def _message_content(data: dict[str, Any]) -> str:
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("OpenAI-compatible response shape is invalid") from exc
    if isinstance(content, str):
        return content
    return json.dumps(content, ensure_ascii=False)
