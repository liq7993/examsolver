"""Graph nodes that wrap existing deterministic pipeline modules."""

from __future__ import annotations

import logging

from examsolver.contracts import NoteEntry
from examsolver.graph.router_agent import route_question
from examsolver.graph.state import SolveGraphState
from examsolver.pipeline.dispatcher import dispatch
from examsolver.pipeline.formatter import format_response
from examsolver.pipeline.normalizer import normalize
from examsolver.services.explanation import enhance_if_needed
from examsolver.skills.base import PersistenceError
from examsolver.skills.registry import unknown_skill
from examsolver.storage.history_repo import save_history

logger = logging.getLogger(__name__)


def normalize_node(state: SolveGraphState) -> SolveGraphState:
    """Normalize raw input into the central question contract."""

    logger.info("[unknown] graph.normalize_node: begin")
    normalized = normalize(state["request"])
    request_id = str(normalized.hints["request_id"])
    logger.info(
        "[%s] graph.normalize_node: done subject=%s images=%s",
        request_id,
        normalized.subject,
        len(normalized.image_paths),
    )
    return {"normalized": normalized}


def router_agent_node(state: SolveGraphState) -> SolveGraphState:
    """Select a question type with the M1 deterministic router fallback."""

    normalized = state["normalized"]
    decision = route_question(normalized)
    request_id = str(normalized.hints.get("request_id", "unknown"))
    logger.info(
        "[%s] graph.router_agent_node: subject=%s question_type=%s confidence=%.2f",
        request_id,
        decision.subject,
        decision.question_type,
        decision.confidence,
    )
    return {
        "subject": decision.subject,
        "question_type": decision.question_type,
        "routing_confidence": decision.confidence,
        "routing_reasoning": decision.reasoning,
    }


def route_after_router(state: SolveGraphState) -> str:
    """Send known types to skills and unsupported types to the general fallback."""

    return "general" if state.get("question_type") == "unknown" else "skill"


def skill_node(state: SolveGraphState) -> SolveGraphState:
    """Run the selected deterministic skill."""

    normalized = state["normalized"]
    request_id = str(normalized.hints.get("request_id", "unknown"))
    try:
        result = dispatch(normalized, state["question_type"])
    except Exception as exc:
        logger.warning("[%s] graph.skill_node: fallback primary_skill_failed: %s", request_id, exc)
        result = unknown_skill().solve(normalized)
        fallback_reasons = [*state.get("fallback_reasons", []), "primary_skill_failed"]
        return {
            "solve_result": result,
            "fallback_reasons": fallback_reasons,
        }

    logger.info("[%s] graph.skill_node: skill=%s", request_id, result.skill)
    return {"solve_result": result}


def general_node(state: SolveGraphState) -> SolveGraphState:
    """M1 general fallback path for unsupported questions."""

    normalized = state["normalized"]
    request_id = str(normalized.hints.get("request_id", "unknown"))
    result = unknown_skill().solve(normalized)
    logger.info("[%s] graph.general_node: skill=%s", request_id, result.skill)
    return {"solve_result": result}


def explanation_enhancer_node(state: SolveGraphState) -> SolveGraphState:
    """Optionally fill the student-facing explanation field."""

    normalized = state["normalized"]
    request_id = str(normalized.hints.get("request_id", "unknown"))
    result = state["solve_result"]
    logger.info("[%s] graph.explanation_enhancer_node: begin", request_id)
    if result.student_explanation is not None:
        logger.info(
            "[%s] graph.explanation_enhancer_node: done has_explanation=%s",
            request_id,
            True,
        )
        return {}

    new_result = enhance_if_needed(
        question=normalized,
        result=result,
        enhancer=state["enhancer"],
    )
    logger.info(
        "[%s] graph.explanation_enhancer_node: done has_explanation=%s",
        request_id,
        new_result.student_explanation is not None,
    )
    return {"solve_result": new_result}


def note_builder_node(state: SolveGraphState) -> SolveGraphState:
    """Build the minimum one-question note shell for later frontend/export work."""

    normalized = state["normalized"]
    result = state["solve_result"]
    solve_id = str(normalized.hints["solve_id"])
    title = _note_title(normalized.normalized_text)
    note = NoteEntry(
        solve_id=solve_id,
        title=title,
        question_latex=normalized.normalized_text,
        steps=result.steps,
        answer=result.answer,
        student_explanation=result.student_explanation,
        common_mistakes=_common_mistakes(result),
        related_formulas=[],
        flashcards=[],
        citations=result.citations,
        subject=normalized.subject,
        question_type=result.question_type,
    )
    request_id = str(normalized.hints.get("request_id", "unknown"))
    logger.info("[%s] graph.note_builder_node: title=%s", request_id, title)
    return {"note": note}


def format_node(state: SolveGraphState) -> SolveGraphState:
    """Format the graph result into the public solve response."""

    normalized = state["normalized"]
    request_id = str(normalized.hints.get("request_id", "unknown"))
    logger.info("[%s] graph.format_node: begin", request_id)
    response = format_response(normalized, state["solve_result"])
    logger.info("[%s] graph.format_node: done success=%s", request_id, response.success)
    return {"response": response}


def persist_node(state: SolveGraphState) -> SolveGraphState:
    """Persist history without failing the solve if SQLite is unavailable."""

    normalized = state["normalized"]
    response = state["response"]
    request_id = str(normalized.hints.get("request_id", "unknown"))
    logger.info("[%s] graph.persist_node: begin", request_id)
    try:
        save_history(question=normalized, response=response)
    except PersistenceError as exc:
        logger.warning("[%s] history save skipped: %s", request_id, exc)
        return {"persistence_error": str(exc)}
    logger.info("[%s] graph.persist_node: done saved solve_id=%s", request_id, response.solve_id)
    return {}


def _note_title(text: str) -> str:
    compact = " ".join(text.split())
    return compact[:32] or "未命名题目"


def _common_mistakes(result: object) -> list[str]:
    explanation = getattr(result, "student_explanation", None)
    mistake = getattr(explanation, "common_mistake", "")
    return [str(mistake)] if str(mistake).strip() else []
