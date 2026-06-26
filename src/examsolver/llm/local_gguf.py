"""Local GGUF LLM client (llama-server) over the OpenAI-compatible API."""

from __future__ import annotations

import httpx

from examsolver.config import load_llm_config
from examsolver.llm.base import Message
from examsolver.llm.openai_compatible import OpenAICompatibleClient

DEFAULT_LOCAL_BASE_URL = "http://127.0.0.1:8080/v1"
DEFAULT_LOCAL_MODEL = "gemma-4-E2B-it-Q4_K_M"


class LocalGGUFClient(OpenAICompatibleClient):
    """OpenAI-compatible client wired to a local llama-server.

    Resolves connection defaults from :func:`examsolver.config.load_llm_config`
    and runs without an API key. The wire protocol, retry policy, and logging
    are inherited unchanged from :class:`OpenAICompatibleClient`.
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        model: str | None = None,
        task_kind: str = "unknown",
        client: httpx.Client | None = None,
    ) -> None:
        config = load_llm_config()
        super().__init__(
            base_url=base_url or config.base_url or DEFAULT_LOCAL_BASE_URL,
            model=model or config.model or DEFAULT_LOCAL_MODEL,
            api_key=None,
            task_kind=task_kind,
            provider_label="local_gguf",
            client=client,
        )

    def chat_with_image(
        self,
        messages: list[Message],
        images: list[bytes],
        **kwargs: object,
    ) -> str:
        """Local text GGUF models cannot see images -- vision degrades elsewhere."""

        _ = (messages, images, kwargs)
        raise NotImplementedError("local GGUF client does not support image input")
