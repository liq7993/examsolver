"""Skill dispatch layer."""

from __future__ import annotations

import logging

from examsolver.contracts import NormalizedQuestion, SolveResult
from examsolver.skills.base import SkillExecutionError
from examsolver.skills.registry import find_skill_for, unknown_skill

logger = logging.getLogger(__name__)


def dispatch(question: NormalizedQuestion, question_type: str) -> SolveResult:
    """Dispatch a normalized question to the selected skill."""

    skill = find_skill_for(question, question_type)
    try:
        result = skill.solve(question)
    except Exception as exc:
        request_id = str(question.hints.get("request_id", "unknown"))
        logger.warning("[%s] skill failed; falling back to unknown: %s", request_id, exc)
        raise SkillExecutionError("skill execution failed", request_id=request_id) from exc

    if result.question_type == "unknown" and result.skill == "unknown":
        return result
    return result


def dispatch_or_unknown(question: NormalizedQuestion, question_type: str) -> SolveResult:
    """Dispatch and convert skill failures to the normal unknown path."""

    try:
        return dispatch(question, question_type)
    except SkillExecutionError:
        return unknown_skill().solve(question)
