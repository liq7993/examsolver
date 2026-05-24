"""Choose an LLM client for a task.

Supported ``task_kind`` values:
``"route" | "extract_simple" | "synthesize" | "explain" | "general_solve"``.

M2-01 only defines the routing seam. Concrete cloud and local clients are added
in later M2 cards, so this function currently returns ``None`` for every input.
"""

from __future__ import annotations

from examsolver.llm.base import LLMClient


def pick_llm(task_kind: str, needs_vision: bool) -> LLMClient | None:
    """Return the configured LLM client for a task, or ``None`` until clients exist."""

    _ = (task_kind, needs_vision)
    return None
