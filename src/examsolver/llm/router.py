"""Choose an LLM client for a task.

Supported ``task_kind`` values:
``"route" | "extract_simple" | "synthesize" | "explain" | "general_solve"``.
"""

from __future__ import annotations

from examsolver.llm.base import LLMClient
from examsolver.llm.claude_client import ClaudeClient
from examsolver.llm.local_gguf import LocalGGUFClient


def pick_llm(task_kind: str, needs_vision: bool) -> LLMClient | None:
    """Return the preferred LLM client for a task."""

    if needs_vision or task_kind in {"synthesize", "explain"}:
        return ClaudeClient(task_kind=task_kind)
    if task_kind in {"route", "extract_simple"}:
        return LocalGGUFClient(task_kind=task_kind)
    return None
