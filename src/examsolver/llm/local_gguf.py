"""OpenAI-compatible local GGUF LLM client for llama-server."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, cast

import httpx

from examsolver.config import load_llm_config
from examsolver.llm.base import Message

DEFAULT_LOCAL_BASE_URL = "http://127.0.0.1:8080/v1"
DEFAULT_LOCAL_MODEL = "gemma-4-E2B-it-Q4_K_M"

logger = logging.getLogger(__name__)


class LocalGGUFClient:
    """Synchronous OpenAI-compatible chat client for a local GGUF server."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        model: str | None = None,
        task_kind: str = "unknown",
        client: httpx.Client | None = None,
    ) -> None:
        config = load_llm_config()
        self.base_url = (base_url or config.base_url or DEFAULT_LOCAL_BASE_URL).rstrip("/")
        self.model = model or config.model or DEFAULT_LOCAL_MODEL
        self.task_kind = task_kind
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

        payload = {
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
        """Local GGUF text clients do not provide VLM support in M2."""

        _ = (messages, images, kwargs)
        raise NotImplementedError("LocalGGUFClient does not support image input")

    def _post(self, payload: dict[str, object], *, timeout: float) -> dict[str, Any]:
        started = time.perf_counter()
        logger.info(
            "[unknown] INFO llm.local_gguf.chat: begin task_kind=%s model=%s",
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
            "[unknown] INFO llm.local_gguf.chat: done task_kind=%s tokens_in=%s "
            "tokens_out=%s latency=%.2fs",
            self.task_kind,
            tokens_in,
            tokens_out,
            latency,
        )
        return cast(dict[str, Any], data)

    def _post_with_retry(self, payload: dict[str, object], *, timeout: float) -> httpx.Response:
        last_error: httpx.RequestError | httpx.HTTPStatusError | None = None
        for attempt in range(2):
            try:
                response = self._client.post(
                    f"{self.base_url}/chat/completions",
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
                    "[unknown] WARNING llm.local_gguf.chat: retry task_kind=%s",
                    self.task_kind,
                )
        if last_error is None:
            raise RuntimeError("local GGUF request failed without an exception")
        raise last_error


def _messages_payload(messages: list[Message]) -> list[dict[str, str]]:
    return [{"role": message.role, "content": message.content} for message in messages]


def _message_content(data: dict[str, Any]) -> str:
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("local GGUF response shape is invalid") from exc
    if isinstance(content, str):
        return content
    return json.dumps(content, ensure_ascii=False)
