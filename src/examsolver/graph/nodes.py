"""Graph nodes that wrap existing deterministic pipeline modules."""

from __future__ import annotations

import importlib
import logging
from dataclasses import replace

from examsolver.graph.router_agent import route_question
from examsolver.graph.state import SolveGraphState
from examsolver.llm.router import pick_llm
from examsolver.multimodal import OCRError
from examsolver.multimodal.ocr_paddle import recognize
from examsolver.notes.note_builder import build_note
from examsolver.pipeline.dispatcher import dispatch
from examsolver.pipeline.formatter import format_response
from examsolver.pipeline.normalizer import normalize
from examsolver.rag import retriever as rag_retriever
from examsolver.services.explanation import enhance_if_needed
from examsolver.skills.base import PersistenceError
from examsolver.skills.general import CotWithTextbookSkill
from examsolver.skills.registry import get_skill, unknown_skill
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


def has_images(state: SolveGraphState) -> str:
    """Route image-bearing requests through OCR before routing."""

    return "ocr" if state["normalized"].image_paths else "router_agent"


def ocr_node(state: SolveGraphState) -> SolveGraphState:
    """Run OCR for image-backed requests without blocking text-only solving."""

    normalized = state["normalized"]
    request_id = str(normalized.hints.get("request_id", "unknown"))
    if not normalized.image_paths:
        _log_info(request_id, "ocr_node", "skip images=0")
        return {}

    _log_info(request_id, "ocr_node", "begin images=%s", len(normalized.image_paths))
    try:
        result = recognize(normalized.image_paths)
    except OCRError as exc:
        _log_warning(request_id, "ocr_node", "fallback ocr_failed: %s", exc)
        return {
            "fallback_reasons": [
                *state.get("fallback_reasons", []),
                f"ocr_failed:{exc}",
            ]
        }
    except Exception as exc:
        _log_warning(request_id, "ocr_node", "fallback ocr_failed: %s", exc)
        return {
            "fallback_reasons": [
                *state.get("fallback_reasons", []),
                f"ocr_failed:{exc}",
            ]
        }

    _log_info(
        request_id,
        "ocr_node",
        "done chars=%s bboxes=%s confidence=%.2f",
        len(result.text),
        len(result.bboxes),
        result.confidence,
    )
    return {"ocr_text": result.text, "ocr_bboxes": result.bboxes}


def router_agent_node(state: SolveGraphState) -> SolveGraphState:
    """Select a question type with regex first and an LLM fallback."""

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
    routed_state: SolveGraphState = {
        "subject": decision.subject,
        "question_type": decision.question_type,
        "routing_confidence": decision.confidence,
        "routing_reasoning": decision.reasoning,
    }
    if decision.fallback_reasons:
        routed_state["fallback_reasons"] = [
            *state.get("fallback_reasons", []),
            *decision.fallback_reasons,
        ]
    return routed_state


def route_after_router(state: SolveGraphState) -> str:
    """Send known types to skills and unsupported types to the general fallback."""

    if _should_retrieve_rag(state):
        return "rag_retrieve"
    return "general" if state.get("question_type") == "unknown" else "skill"


def route_after_rag(state: SolveGraphState) -> str:
    """Continue to the original solve branch after optional RAG retrieval."""

    return "general" if state.get("question_type") == "unknown" else "skill"


def rag_retrieve_node(state: SolveGraphState) -> SolveGraphState:
    """Retrieve textbook chunks for subjects or skills that declare RAG support."""

    normalized = state["normalized"]
    request_id = str(normalized.hints.get("request_id", "unknown"))
    subject = state.get("subject") or normalized.subject
    if not _should_retrieve_rag(state):
        _log_info(request_id, "rag_retrieve_node", "skip subject=%s", subject)
        return {"retrieved_chunks": []}

    _log_info(request_id, "rag_retrieve_node", "begin subject=%s", subject)
    chunks = rag_retriever.retrieve(query=normalized.normalized_text, subject=subject)
    _log_info(request_id, "rag_retrieve_node", "done chunks=%s", len(chunks))
    return {"retrieved_chunks": chunks}


def skill_node(state: SolveGraphState) -> SolveGraphState:
    """Run the selected deterministic skill."""

    normalized = state["normalized"]
    routed_question = replace(normalized, subject=state.get("subject", normalized.subject))
    request_id = str(normalized.hints.get("request_id", "unknown"))
    try:
        result = dispatch(
            routed_question,
            state["question_type"],
            rag_chunks=state.get("retrieved_chunks", []),
        )
    except Exception as exc:
        _log_warning(request_id, "skill_node", "fallback primary_skill_failed: %s", exc)
        result = unknown_skill().solve(routed_question)
        fallback_reasons = [*state.get("fallback_reasons", []), "primary_skill_failed"]
        return {
            "solve_result": result,
            "fallback_reasons": fallback_reasons,
        }

    _log_info(request_id, "skill_node", "skill=%s", result.skill)
    return {"solve_result": result}


def general_node(state: SolveGraphState) -> SolveGraphState:
    """Run the general Type-L fallback skill for unsupported questions."""

    normalized = state["normalized"]
    request_id = str(normalized.hints.get("request_id", "unknown"))
    try:
        llm = pick_llm("general_solve", needs_vision=False)
        result = CotWithTextbookSkill().solve(normalized, llm=llm)
    except Exception as exc:
        _log_warning(request_id, "general_node", "fallback general_skill_failed: %s", exc)
        result = unknown_skill().solve(normalized)
        fallback_reasons = [*state.get("fallback_reasons", []), "general_skill_failed"]
        return {
            "solve_result": result,
            "fallback_reasons": fallback_reasons,
        }
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
    note = replace(
        build_note(state["solve_result"], normalized),
        subject=state.get("subject", normalized.subject),
    )
    _log_info(request_id, "note_builder_node", "done title=%s", note.title)
    return {"note": note}


def format_node(state: SolveGraphState) -> SolveGraphState:
    """Format the graph result into the public solve response."""

    normalized = state["normalized"]
    request_id = str(normalized.hints.get("request_id", "unknown"))
    _log_info(request_id, "format_node", "begin")
    response = replace(
        format_response(normalized, state["solve_result"]),
        subject=state.get("subject", normalized.subject),
        note=state.get("note"),
        fallback_reasons=state.get("fallback_reasons", []),
    )
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


def _should_retrieve_rag(state: SolveGraphState) -> bool:
    normalized = state.get("normalized")
    subject = state.get("subject") or (normalized.subject if normalized is not None else None)
    question_type = state.get("question_type", "")
    return _subject_has_textbook(subject) or _skill_needs_rag(subject, question_type)


def _subject_has_textbook(subject: str | None) -> bool:
    if not subject:
        return False
    try:
        module = importlib.import_module(f"examsolver.skills.{subject}._meta")
    except ModuleNotFoundError:
        return False
    meta = getattr(module, "SUBJECT_META", {})
    return isinstance(meta, dict) and meta.get("has_textbook") is True


def _skill_needs_rag(subject: str | None, question_type: str | None) -> bool:
    if not subject or not question_type:
        return False
    skill = get_skill(subject, question_type)
    return bool(getattr(skill, "needs_rag", False))
