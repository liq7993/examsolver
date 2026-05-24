"""Anthropic Claude implementation of the LLM client Protocol."""

from __future__ import annotations

import base64
import json
import logging
import os
import time
from typing import Any, cast

import httpx

from examsolver.llm.base import Message

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-20250514"
STRUCTURED_OUTPUT_TOOL = "emit_structured_output"

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Synchronous Claude Messages API client backed by httpx."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        task_kind: str = "unknown",
        client: httpx.Client | None = None,
    ) -> None:
        selected_api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not selected_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for ClaudeClient")

        self._api_key = selected_api_key
        self.model = model or os.getenv("EXAMSOLVER_CLAUDE_MODEL", DEFAULT_CLAUDE_MODEL)
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
        """Return Claude's text response or structured tool input as JSON text."""

        payload = self._payload(
            messages=messages,
            extra_images=[],
            json_schema=json_schema,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        data = self._post(payload, timeout=timeout)
        if json_schema is not None:
            return json.dumps(_tool_input(data), ensure_ascii=False)
        return _text_content(data)

    def chat_with_image(
        self,
        messages: list[Message],
        images: list[bytes],
        **kwargs: object,
    ) -> str:
        """Return Claude's response for messages with PNG image bytes."""

        json_schema = cast(dict[str, object] | None, kwargs.get("json_schema"))
        max_tokens = _int_kwarg(kwargs, "max_tokens", 1024)
        temperature = _float_kwarg(kwargs, "temperature", 0.2)
        timeout = _float_kwarg(kwargs, "timeout", 30.0)
        payload = self._payload(
            messages=messages,
            extra_images=images,
            json_schema=json_schema,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        data = self._post(payload, timeout=timeout)
        if json_schema is not None:
            return json.dumps(_tool_input(data), ensure_ascii=False)
        return _text_content(data)

    def _payload(
        self,
        *,
        messages: list[Message],
        extra_images: list[bytes],
        json_schema: dict[str, object] | None,
        max_tokens: int,
        temperature: float,
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": _messages_payload(messages, extra_images=extra_images),
        }
        system_prompt = _system_prompt(messages)
        if system_prompt:
            payload["system"] = system_prompt
        if json_schema is not None:
            payload["tools"] = [
                {
                    "name": STRUCTURED_OUTPUT_TOOL,
                    "description": "Return the response exactly in this structured shape.",
                    "input_schema": json_schema,
                    "strict": True,
                }
            ]
            payload["tool_choice"] = {"type": "tool", "name": STRUCTURED_OUTPUT_TOOL}
        return payload

    def _post(self, payload: dict[str, object], *, timeout: float) -> dict[str, Any]:
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }
        started = time.perf_counter()
        logger.info(
            "[unknown] INFO llm.claude_client.chat: begin task_kind=%s model=%s",
            self.task_kind,
            self.model,
        )
        response = self._post_with_retry(payload, headers=headers, timeout=timeout)
        latency = time.perf_counter() - started
        data = response.json()
        usage = data.get("usage") if isinstance(data, dict) else {}
        tokens_in = usage.get("input_tokens", 0) if isinstance(usage, dict) else 0
        tokens_out = usage.get("output_tokens", 0) if isinstance(usage, dict) else 0
        logger.info(
            "[unknown] INFO llm.claude_client.chat: done task_kind=%s tokens_in=%s "
            "tokens_out=%s latency=%.2fs",
            self.task_kind,
            tokens_in,
            tokens_out,
            latency,
        )
        return cast(dict[str, Any], data)

    def _post_with_retry(
        self,
        payload: dict[str, object],
        *,
        headers: dict[str, str],
        timeout: float,
    ) -> httpx.Response:
        last_error: httpx.RequestError | httpx.HTTPStatusError | None = None
        for attempt in range(2):
            try:
                response = self._client.post(
                    ANTHROPIC_MESSAGES_URL,
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
                    "[unknown] WARNING llm.claude_client.chat: retry task_kind=%s",
                    self.task_kind,
                )
        if last_error is None:
            raise RuntimeError("Claude request failed without an exception")
        raise last_error


def _messages_payload(messages: list[Message], *, extra_images: list[bytes]) -> list[dict[str, object]]:
    payload_messages: list[dict[str, object]] = []
    extra_images_added = False
    for message in messages:
        if message.role == "system":
            continue
        images = message.images
        if message.role == "user" and extra_images and not extra_images_added:
            images = [*extra_images, *images]
            extra_images_added = True
        payload_messages.append(
            {
                "role": message.role,
                "content": _content_payload(message.content, images=images),
            }
        )
    if extra_images and not extra_images_added:
        payload_messages.append(
            {
                "role": "user",
                "content": _content_payload("", images=extra_images),
            }
        )
    return payload_messages


def _content_payload(content: str, *, images: list[bytes]) -> str | list[dict[str, object]]:
    if not images:
        return content
    blocks: list[dict[str, object]] = [_image_block(image) for image in images]
    if content:
        blocks.append({"type": "text", "text": content})
    return blocks


def _image_block(image: bytes) -> dict[str, object]:
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": "image/png",
            "data": base64.b64encode(image).decode("ascii"),
        },
    }


def _system_prompt(messages: list[Message]) -> str | None:
    prompts = [message.content for message in messages if message.role == "system"]
    return "\n\n".join(prompts) if prompts else None


def _int_kwarg(kwargs: dict[str, object], name: str, default: int) -> int:
    value = kwargs.get(name, default)
    if isinstance(value, int):
        return value
    raise TypeError(f"{name} must be an int")


def _float_kwarg(kwargs: dict[str, object], name: str, default: float) -> float:
    value = kwargs.get(name, default)
    if isinstance(value, int | float):
        return float(value)
    raise TypeError(f"{name} must be a float")


def _text_content(data: dict[str, Any]) -> str:
    content = data.get("content", [])
    if not isinstance(content, list):
        return ""
    return "".join(
        block.get("text", "")
        for block in content
        if isinstance(block, dict) and block.get("type") == "text"
    )


def _tool_input(data: dict[str, Any]) -> dict[str, Any]:
    content = data.get("content", [])
    if not isinstance(content, list):
        raise ValueError("Claude response content is not a list")
    for block in content:
        if (
            isinstance(block, dict)
            and block.get("type") == "tool_use"
            and block.get("name") == STRUCTURED_OUTPUT_TOOL
            and isinstance(block.get("input"), dict)
        ):
            return cast(dict[str, Any], block["input"])
    raise ValueError("Claude response did not include the structured output tool")
