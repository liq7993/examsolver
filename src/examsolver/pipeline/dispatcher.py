"""Skill dispatch layer."""

from __future__ import annotations

import inspect
import logging
from collections.abc import Sequence
from typing import Any, cast

from examsolver.contracts import NormalizedQuestion, SolveResult
from examsolver.rag.retriever import TextbookChunk
from examsolver.skills.base import SkillExecutionError
from examsolver.skills.registry import find_skill_for, unknown_skill

logger = logging.getLogger(__name__)


def dispatch(
    question: NormalizedQuestion,
    question_type: str,
    *,
    rag_chunks: Sequence[TextbookChunk] | None = None,
) -> SolveResult:
    """Dispatch a normalized question to the selected skill."""

    skill = find_skill_for(question, question_type)
    try:
        if rag_chunks is not None and "rag_chunks" in inspect.signature(skill.solve).parameters:
            result = cast(SolveResult, cast(Any, skill).solve(question, rag_chunks=list(rag_chunks)))
        else:
            result = skill.solve(question)
    except Exception as exc:
        request_id = str(question.hints.get("request_id", "unknown"))
        logger.warning("[%s] skill failed; falling back to unknown: %s", request_id, exc)
        raise SkillExecutionError("skill execution failed", request_id=request_id) from exc

    if result.question_type == "unknown" and result.skill == "unknown":
        return result
    return result


def dispatch_or_unknown(
    question: NormalizedQuestion,
    question_type: str,
    *,
    rag_chunks: Sequence[TextbookChunk] | None = None,
) -> SolveResult:
    """Dispatch and convert skill failures to the normal unknown path."""

    try:
        return dispatch(question, question_type, rag_chunks=rag_chunks)
    except SkillExecutionError:
        return unknown_skill().solve(question)
