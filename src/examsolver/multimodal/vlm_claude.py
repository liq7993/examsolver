"""Cloud VLM adapter for image-to-description extraction."""

from __future__ import annotations

import logging

import httpx

from examsolver.llm import ClaudeClient, Message
from examsolver.llm.router import pick_llm
from examsolver.multimodal import VLMError

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "你是 Examsolver 的图像描述器。只描述图片中能直接看见的题面、机构、"
    "符号、齿数、标注和几何关系；不要解题，不要推导答案，不要补全看不清的信息。"
)


class ClaudeVLMClient:
    """Describe images with Claude vision without solving the question."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        try:
            self._claude = ClaudeClient(
                api_key=api_key,
                model=model,
                task_kind="vision_description",
                client=client,
            )
        except ValueError as exc:
            raise VLMError("ANTHROPIC_API_KEY is required for Claude VLM") from exc

    def describe(
        self,
        images: list[bytes],
        prompt: str,
        *,
        max_tokens: int = 512,
        temperature: float = 0.0,
        timeout: float = 30.0,
    ) -> str:
        """Return a natural-language description of visible image content."""

        if not images:
            raise VLMError("at least one image is required for VLM description")

        logger.info(
            "[unknown] INFO multimodal.vlm_claude.describe: begin image_count=%s",
            len(images),
        )
        try:
            description = self._claude.chat_with_image(
                [
                    Message(role="system", content=_SYSTEM_PROMPT),
                    Message(role="user", content=prompt),
                ],
                images,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout,
            ).strip()
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise VLMError("Claude VLM description failed") from exc

        if not description:
            raise VLMError("Claude VLM returned an empty description")

        logger.info("[unknown] INFO multimodal.vlm_claude.describe: done")
        return description


def describe(images: list[bytes], prompt: str) -> str:
    """Describe images using whichever vision model is configured.

    Provider-agnostic: routes through ``pick_llm(needs_vision=True)`` so any
    configured vision-capable provider (cloud OpenAI-compatible or Claude) is used.
    Degrades to ``VLMError`` when none is available or the call fails -- never
    fabricates a description.
    """

    if not images:
        raise VLMError("at least one image is required for VLM description")
    try:
        client = pick_llm("vision_description", needs_vision=True)
    except ValueError as exc:  # e.g. Claude selected but its key is missing
        raise VLMError("no vision-capable model is available") from exc
    if client is None:
        raise VLMError("no vision-capable model is configured")

    logger.info("[unknown] INFO multimodal.describe: begin image_count=%s", len(images))
    try:
        description = client.chat_with_image(
            [
                Message(role="system", content=_SYSTEM_PROMPT),
                Message(role="user", content=prompt),
            ],
            images,
            max_tokens=512,
            temperature=0.0,
            timeout=30.0,
        ).strip()
    except (httpx.HTTPError, ValueError, TypeError, NotImplementedError) as exc:
        raise VLMError("vision description failed") from exc

    if not description:
        raise VLMError("VLM returned an empty description")
    logger.info("[unknown] INFO multimodal.describe: done")
    return description
