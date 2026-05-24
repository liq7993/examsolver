"""Graph nodes that wrap existing deterministic pipeline modules."""

from __future__ import annotations

import logging
from dataclasses import replace

from examsolver.graph.router_agent import route_question
from examsolver.graph.state import SolveGraphState
from examsolver.notes.note_builder import build_note
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

    _log_info("unknown", "normalize_node", "begin")
    normalized = normalize(state["request"])
    request_id = str(normalized.hints["request_id"])
    _log_info(
        request_id,
        "normalize_node",
        "done subject=%s images=%s",
        normalized.subject,
        len(normalized.image_paths),
    )
    return {"normalized": normalized}


def router_agent_node(state: SolveGraphState) -> SolveGraphState:
    """Select a question type with the M1 deterministic router fallback."""

    normalized = state["normalized"]
    decision = route_question(normalized)
    request_id = str(normalized.hints.get("request_id", "unknown"))
    _log_info(
        request_id,
        "router_agent_node",
        "subject=%s question_type=%s confidence=%.2f",
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
        _log_warning(request_id, "skill_node", "fallback primary_skill_failed: %s", exc)
        result = unknown_skill().solve(normalized)
        fallback_reasons = [*state.get("fallback_reasons", []), "primary_skill_failed"]
        return {
            "solve_result": result,
            "fallback_reasons": fallback_reasons,
        }

    _log_info(request_id, "skill_node", "skill=%s", result.skill)
    return {"solve_result": result}


def general_node(state: SolveGraphState) -> SolveGraphState:
    """M1 general fallback path for unsupported questions."""

    normalized = state["normalized"]
    request_id = str(normalized.hints.get("request_id", "unknown"))
    result = unknown_skill().solve(normalized)
    _log_info(request_id, "general_node", "skill=%s", result.skill)
    return {"solve_result": result}


def explanation_enhancer_node(state: SolveGraphState) -> SolveGraphState:
    """Optionally fill the student-facing explanation field."""

    normalized = state["normalized"]
    request_id = str(normalized.hints.get("request_id", "unknown"))
    result = state["solve_result"]
    _log_info(request_id, "explanation_enhancer_node", "begin")
    if result.student_explanation is not None:
        _log_info(
            request_id,
            "explanation_enhancer_node",
            "done has_explanation=%s",
            True,
        )
        return {}

    new_result = enhance_if_needed(
        question=normalized,
        result=result,
        enhancer=state["enhancer"],
    )
    _log_info(
        request_id,
        "explanation_enhancer_node",
        "done has_explanation=%s",
        new_result.student_explanation is not None,
    )
    return {"solve_result": new_result}


def note_builder_node(state: SolveGraphState) -> SolveGraphState:
    """Build the minimum one-question note shell for later frontend/export work."""

    normalized = state["normalized"]
    request_id = str(normalized.hints.get("request_id", "unknown"))
    _log_info(request_id, "note_builder_node", "begin")
    note = build_note(state["solve_result"], normalized)
    _log_info(request_id, "note_builder_node", "done title=%s", note.title)
    return {"note": note}


def format_node(state: SolveGraphState) -> SolveGraphState:
    """Format the graph result into the public solve response."""

    normalized = state["normalized"]
    request_id = str(normalized.hints.get("request_id", "unknown"))
    _log_info(request_id, "format_node", "begin")
    response = replace(format_response(normalized, state["solve_result"]), note=state.get("note"))
    _log_info(request_id, "format_node", "done success=%s", response.success)
    return {"response": response}


def persist_node(state: SolveGraphState) -> SolveGraphState:
    """Persist history without failing the solve if SQLite is unavailable."""

    normalized = state["normalized"]
    response = state["response"]
    request_id = str(normalized.hints.get("request_id", "unknown"))
    _log_info(request_id, "persist_node", "begin")
    try:
        save_history(question=normalized, response=response)
    except PersistenceError as exc:
        _log_warning(request_id, "persist_node", "history save skipped: %s", exc)
        return {"persistence_error": str(exc)}
    _log_info(request_id, "persist_node", "done saved solve_id=%s", response.solve_id)
    return {}


def _log_info(request_id: str, function: str, message: str, *args: object) -> None:
    logger.info("[%s] INFO graph.nodes.%s: " + message, request_id, function, *args)


def _log_warning(request_id: str, function: str, message: str, *args: object) -> None:
    logger.warning("[%s] WARNING graph.nodes.%s: " + message, request_id, function, *args)
