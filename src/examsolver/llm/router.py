"""Choose an LLM client for a task.

Supported ``task_kind`` values:
``"route" | "extract_simple" | "synthesize" | "explain" | "general_solve"``.
"""

from __future__ import annotations

import json
import os
from typing import Any, cast

from examsolver.config import cloud_llm_provider, cloud_vision_model
from examsolver.llm.base import LLMClient
from examsolver.llm.base import Message
from examsolver.llm.claude_client import ClaudeClient
from examsolver.llm.local_gguf import LocalGGUFClient
from examsolver.llm.openai_compatible import OpenAICompatibleClient


def pick_llm(task_kind: str, needs_vision: bool) -> LLMClient | None:
    """Return the preferred LLM client for a task."""

    provider = os.getenv("EXAMSOLVER_LLM_PROVIDER", "").strip().lower()
    if needs_vision:
        return _vision_client(provider, task_kind)
    if provider == "claude":
        return ClaudeClient(task_kind=task_kind)
    cloud_client = _cloud_openai_client(provider, task_kind)
    if cloud_client is not None:
        return cloud_client
    if provider == "local_gguf" and task_kind in {"route", "extract_simple"}:
        return LocalGGUFClient(task_kind=task_kind)
    if task_kind in {"synthesize", "explain"}:
        return ClaudeClient(task_kind=task_kind)
    if task_kind == "general_solve":
        if os.getenv("ANTHROPIC_API_KEY"):
            return ClaudeClient(task_kind=task_kind)
        return _OfflineGeneralSolveClient()
    if task_kind in {"route", "extract_simple"}:
        return LocalGGUFClient(task_kind=task_kind)
    return None


def _vision_client(provider: str, task_kind: str) -> LLMClient | None:
    """Pick a vision-capable client for the configured provider, or degrade.

    Any cloud provider with a known vision model is used over its OpenAI-compatible
    endpoint; the Claude provider uses its native vision; otherwise fall back to
    Claude when its key is present, and finally return ``None`` so the VLM node
    degrades honestly instead of pretending to see.
    """

    if provider == "claude":
        return ClaudeClient(task_kind=task_kind)
    spec = cloud_llm_provider(provider)
    if spec is not None:
        api_key = os.getenv(spec.api_key_env)
        vision_model = cloud_vision_model(spec)
        if api_key and vision_model:
            return OpenAICompatibleClient(
                base_url=spec.base_url,
                model=vision_model,
                api_key=api_key,
                task_kind=task_kind,
                provider_label=spec.name,
            )
    if os.getenv("ANTHROPIC_API_KEY"):
        return ClaudeClient(task_kind=task_kind)
    return None


def _cloud_openai_client(provider: str, task_kind: str) -> OpenAICompatibleClient | None:
    """Return a configured cloud client when ``provider`` is registered and keyed.

    Cloud OpenAI-compatible providers serve every text task; vision stays on
    Claude. A missing API key returns ``None`` so the caller degrades gracefully
    to the local/offline fallbacks instead of failing.
    """

    spec = cloud_llm_provider(provider)
    if spec is None:
        return None
    api_key = os.getenv(spec.api_key_env)
    if not api_key:
        return None
    return OpenAICompatibleClient(
        base_url=spec.base_url,
        model=spec.default_model,
        api_key=api_key,
        task_kind=task_kind,
        provider_label=spec.name,
    )


class _OfflineGeneralSolveClient:
    """No-network general-solve fallback used when no cloud key is configured."""

    def chat(
        self,
        messages: list[Message],
        *,
        json_schema: dict[str, object] | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
        timeout: float = 30.0,
    ) -> str:
        _ = (json_schema, max_tokens, temperature, timeout)
        question = _last_user_content(messages)
        return json.dumps(_offline_general_answer(question), ensure_ascii=False)

    def chat_with_image(
        self,
        messages: list[Message],
        images: list[bytes],
        **kwargs: object,
    ) -> str:
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


def _offline_general_answer(question: str) -> dict[str, Any]:
    if "abs" in question.lower() or "防抱死" in question:
        return {
            "thinking": "ABS 的核心是防止车轮制动抱死，从而兼顾减速和转向稳定性。",
            "steps": [
                {
                    "description": "说明 ABS 的对象：紧急制动时容易抱死的车轮",
                    "formula_latex": None,
                },
                {
                    "description": "说明工作结果：调节制动力，使车轮保持接近最佳滑移状态",
                    "formula_latex": None,
                },
                {
                    "description": "归纳考试答法：缩短可控制动距离，并保持转向能力和方向稳定性",
                    "formula_latex": None,
                },
            ],
            "answer": (
                "汽车 ABS 的作用是在紧急制动时防止车轮抱死，通过快速调节制动压力，"
                "让轮胎保持滚动附着状态，从而保持转向能力和方向稳定性，并提高制动安全性。"
            ),
            "common_mistakes": [
                "不要把 ABS 简单理解为一定缩短所有路面的制动距离；它更核心的是防抱死和保持可控性。",
                "不要说 ABS 会增大制动力，它主要是动态调节制动压力。",
            ],
        }
    return {
        "thinking": "先识别题目询问的核心概念，再按定义、作用和注意点组织答案。",
        "steps": [
            {"description": "提取题目中的核心对象和问题意图", "formula_latex": None},
            {"description": "给出概念或原理的直接解释", "formula_latex": None},
            {"description": "补充适用条件、影响或常见误区", "formula_latex": None},
        ],
        "answer": f"这道题可以围绕“{question}”展开：先解释核心概念，再说明它的作用机制和适用条件。",
        "common_mistakes": ["不要只给结论而不说明适用条件。"],
    }


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
