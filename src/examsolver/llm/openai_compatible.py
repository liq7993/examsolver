"""OpenAI-compatible ``/chat/completions`` client.

A single synchronous client for any server speaking the OpenAI chat-completions
wire format. It backs both the local llama-server
(:class:`~examsolver.llm.local_gguf.LocalGGUFClient`, no API key) and hosted
cloud providers (DeepSeek, Moonshot, OpenAI, ...) which authenticate with a
``Bearer`` token. The request shape, retry policy, and logging are identical
across backends, so they live here once.
"""

from __future__ import annotations

import base64
import json
import logging
import time
from typing import Any, cast

import httpx

from examsolver.llm.base import Message

logger = logging.getLogger(__name__)

# The ``name`` we give the json_schema response_format. Some providers (MiniMax)
# echo the structured result nested under this name, so we unwrap it by the same
# constant on the way out -- keep the two uses in sync.
_SCHEMA_NAME = "structured_output"


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
                    "name": _SCHEMA_NAME,
                    "schema": json_schema,
                    "strict": True,
                },
            }

        try:
            data = self._post(payload, timeout=timeout)
        except httpx.HTTPStatusError as exc:
            # Not every OpenAI-compatible provider supports
            # ``response_format: json_schema``. MiniMax, for instance, rejects
            # complex schemas with 400 (and even wraps the output under the
            # schema name when it does accept a simple one). Degrade once to a
            # plain request and lean on the prompt plus the caller's tolerant
            # JSON parsing, so structured output stays best-effort across
            # providers instead of hard-failing the whole solve.
            if json_schema is None or exc.response.status_code != 400:
                raise
            logger.warning(
                "[unknown] WARNING llm.%s.chat: response_format rejected (400), "
                "retrying without schema task_kind=%s",
                self.provider_label,
                self.task_kind,
            )
            payload.pop("response_format", None)
            data = self._post(payload, timeout=timeout)
        content = _message_content(data)
        if json_schema is not None:
            content = _unwrap_structured_output(content)
        return content

    def chat_with_image(
        self,
        messages: list[Message],
        images: list[bytes],
        **kwargs: object,
    ) -> str:
        """Return a response for a multimodal request via OpenAI ``image_url`` parts.

        Images are inlined as base64 data URLs on the last user message -- the
        format OpenAI, MiniMax, and other OpenAI-compatible vision endpoints share.
        A text-only model/provider rejects this, and the caller degrades honestly.
        """

        json_schema = cast(dict[str, object] | None, kwargs.get("json_schema"))
        max_tokens = _int_kwarg(kwargs, "max_tokens", 1024)
        temperature = _float_kwarg(kwargs, "temperature", 0.2)
        timeout = _float_kwarg(kwargs, "timeout", 30.0)
        payload: dict[str, object] = {
            "model": self.model,
            "messages": _vision_messages_payload(messages, images),
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if json_schema is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": _SCHEMA_NAME, "schema": json_schema, "strict": True},
            }
        data = self._post(payload, timeout=timeout)
        content = _message_content(data)
        if json_schema is not None:
            content = _unwrap_structured_output(content)
        return content

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


def _vision_messages_payload(
    messages: list[Message], images: list[bytes]
) -> list[dict[str, Any]]:
    image_parts: list[dict[str, Any]] = [
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{base64.b64encode(image).decode('ascii')}"},
        }
        for image in images
    ]
    last_user_index = max(
        (index for index, message in enumerate(messages) if message.role == "user"),
        default=-1,
    )
    payload: list[dict[str, Any]] = []
    for index, message in enumerate(messages):
        if index == last_user_index:
            payload.append(
                {
                    "role": message.role,
                    "content": [{"type": "text", "text": message.content}, *image_parts],
                }
            )
        else:
            payload.append({"role": message.role, "content": message.content})
    if last_user_index == -1:
        payload.append({"role": "user", "content": image_parts})
    return payload


def _int_kwarg(kwargs: dict[str, object], name: str, default: int) -> int:
    value = kwargs.get(name, default)
    return value if isinstance(value, int) else default


def _float_kwarg(kwargs: dict[str, object], name: str, default: float) -> float:
    value = kwargs.get(name, default)
    return float(value) if isinstance(value, int | float) else default


def _message_content(data: dict[str, Any]) -> str:
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("OpenAI-compatible response shape is invalid") from exc
    if isinstance(content, str):
        return content
    return json.dumps(content, ensure_ascii=False)


def _unwrap_structured_output(content: str) -> str:
    """Peel MiniMax's ``{"structured_output": {...}}`` envelope when present.

    With ``response_format: json_schema`` some providers (MiniMax) return the
    result nested under the schema ``name`` we sent instead of at the top level,
    which makes every caller's tolerant JSON parsing miss the payload. We unwrap
    exactly that single-key envelope so structured output is uniform across
    providers. Best-effort: anything we cannot parse is returned unchanged.
    """

    try:
        parsed = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return content
    if isinstance(parsed, dict) and set(parsed) == {_SCHEMA_NAME}:
        return json.dumps(parsed[_SCHEMA_NAME], ensure_ascii=False)
    return content
