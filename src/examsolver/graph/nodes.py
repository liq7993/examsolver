"""Graph nodes that wrap existing deterministic pipeline modules."""

from __future__ import annotations

import importlib
import logging
from pathlib import Path
from dataclasses import replace

from examsolver.contracts import NormalizedQuestion
from examsolver.graph.router_agent import route_question
from examsolver.graph.state import SolveGraphState
from examsolver.llm.router import pick_llm
from examsolver.multimodal import OCRError, VLMError
from examsolver.multimodal.fallback import check_cloud_reachable
from examsolver.multimodal.ocr_paddle import recognize
from examsolver.multimodal.vlm_claude import describe as describe_images
from examsolver.notes.note_builder import build_note
from examsolver.pipeline.classifier import classify
from examsolver.pipeline.dispatcher import dispatch
from examsolver.pipeline.formatter import format_response
from examsolver.pipeline.normalizer import _infer_subject, normalize
from examsolver.rag import retriever as rag_retriever
from examsolver.services.agentic_solve import agentic_solve
from examsolver.services.explanation import enhance_if_needed
from examsolver.services.plot import attach_plot
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

    normalized = _normalized_with_multimodal_context(state)
    decision = route_question(normalized)
    request_id = str(normalized.hints.get("request_id", "unknown"))
    needs_vision = _needs_vision(normalized)
    # Multi-step questions (二阶导 = differentiate twice, A·B·C = chained matmul)
    # would otherwise regex-classify as a single type and be solved only partially;
    # route them to the agentic orchestrator instead.
    question_type = "multi_step" if _is_multi_step(normalized) else decision.question_type
    _log_info(
        request_id,
        "router_agent_node",
        "subject=%s question_type=%s confidence=%.2f needs_vision=%s",
        decision.subject,
        question_type,
        decision.confidence,
        needs_vision,
    )
    routed_state: SolveGraphState = {
        "normalized": normalized,
        "subject": decision.subject,
        "question_type": question_type,
        "routing_confidence": decision.confidence,
        "routing_reasoning": decision.reasoning,
        "needs_vision": needs_vision,
    }
    if decision.fallback_reasons:
        routed_state["fallback_reasons"] = [
            *state.get("fallback_reasons", []),
            *decision.fallback_reasons,
        ]
    return routed_state


def route_after_router_agent(state: SolveGraphState) -> str:
    """Run VLM only for image requests that need visual understanding."""

    return "vlm" if state.get("needs_vision") else route_after_router(state)


def route_after_vlm(state: SolveGraphState) -> str:
    """Continue along the original post-router branch after optional VLM."""

    return route_after_router(state)


def vlm_node(state: SolveGraphState) -> SolveGraphState:
    """Generate an image description or honestly mark cloud vision unavailable."""

    normalized = state["normalized"]
    request_id = str(normalized.hints.get("request_id", "unknown"))
    if not state.get("needs_vision"):
        _log_info(request_id, "vlm_node", "skip needs_vision=false")
        return {}

    if not check_cloud_reachable():
        _log_warning(request_id, "vlm_node", "fallback vlm_offline")
        return {
            "vision_description": "",
            "normalized": replace(normalized, vision_description=""),
            "fallback_reasons": [*state.get("fallback_reasons", []), "vlm_offline"],
        }

    _log_info(request_id, "vlm_node", "begin images=%s", len(normalized.image_paths))
    try:
        images = [_read_image_bytes(path) for path in normalized.image_paths]
        description = describe_images(images, _vision_prompt(normalized))
    except (OSError, VLMError) as exc:
        _log_warning(request_id, "vlm_node", "fallback vlm_failed: %s", exc)
        return {
            "vision_description": "",
            "normalized": replace(normalized, vision_description=""),
            "fallback_reasons": [*state.get("fallback_reasons", []), "vlm_failed"],
        }

    _log_info(request_id, "vlm_node", "done chars=%s", len(description))
    return {
        "vision_description": description,
        "normalized": replace(normalized, vision_description=description),
    }


def route_after_router(state: SolveGraphState) -> str:
    """Route: multi-step to the agentic loop, known types to skills, rest to general."""

    if state.get("question_type") == "multi_step":
        return "agentic"
    if _should_retrieve_rag(state):
        return "rag_retrieve"
    return "general" if state.get("question_type") == "unknown" else "skill"


def route_after_rag(state: SolveGraphState) -> str:
    """Continue to the original solve branch after optional RAG retrieval."""

    if state.get("question_type") == "multi_step":
        return "agentic"
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


def agentic_solve_node(state: SolveGraphState) -> SolveGraphState:
    """Solve a multi-step question by orchestrating deterministic skills."""

    normalized = state["normalized"]
    request_id = str(normalized.hints.get("request_id", "unknown"))
    routed_question = replace(normalized, subject=state.get("subject", normalized.subject))
    try:
        llm = pick_llm("general_solve", needs_vision=False)
        result = agentic_solve(routed_question, llm=llm)
    except Exception as exc:
        _log_warning(request_id, "agentic_solve_node", "fallback agentic_failed: %s", exc)
        result = unknown_skill().solve(routed_question)
        return {
            "solve_result": result,
            "fallback_reasons": [*state.get("fallback_reasons", []), "agentic_failed"],
        }
    _log_info(
        request_id, "agentic_solve_node", "skill=%s steps=%s", result.skill, len(result.steps)
    )
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


def plot_node(state: SolveGraphState) -> SolveGraphState:
    """Attach a deterministic function plot when the result is plottable.

    Plotting is best-effort: any failure degrades honestly to no plot and never
    breaks the solve pipeline.
    """

    normalized = state["normalized"]
    request_id = str(normalized.hints.get("request_id", "unknown"))
    result = state["solve_result"]
    _log_info(request_id, "plot_node", "begin")
    try:
        new_result = attach_plot(result)
    except Exception as exc:
        _log_warning(request_id, "plot_node", "plot skipped: %s", exc)
        return {}
    _log_info(request_id, "plot_node", "done has_plot=%s", new_result.plot is not None)
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


def _normalized_with_multimodal_context(state: SolveGraphState) -> NormalizedQuestion:
    normalized = state["normalized"]
    ocr_text = state.get("ocr_text", normalized.ocr_text)
    vision_description = state.get("vision_description", normalized.vision_description)
    enriched = replace(
        normalized,
        ocr_text=ocr_text,
        vision_description=vision_description,
    )
    # Fold image-derived text into the question only when the typed text cannot be
    # classified on its own. This is what turns "a photo of a problem" into a
    # solvable question (router + skills read normalized_text), while leaving clear
    # typed questions -- and their note title -- untouched.
    image_text = "\n".join(
        part for part in (ocr_text.strip(), vision_description.strip()) if part
    )
    if image_text and classify(enriched) == "unknown":
        base = enriched.normalized_text.strip()
        merged = f"{base}\n{image_text}".strip() if base else image_text
        subject = enriched.subject
        if subject in ("", "unknown", "general"):
            subject = _infer_subject(merged)
        enriched = replace(enriched, normalized_text=merged, subject=subject)
    return enriched


def _needs_vision(normalized: NormalizedQuestion) -> bool:
    if not normalized.image_paths:
        return False
    text = normalized.normalized_text
    has_visual_keyword = any(keyword in text for keyword in ("图", "机构", "画", "所示"))
    has_short_ocr = len(normalized.ocr_text.strip()) < 20
    return has_visual_keyword or has_short_ocr


_MULTI_STEP_MARKERS = (
    "二阶导",
    "三阶导",
    "高阶导",
    "的导数的导数",
    "再求导",
    "再对",
    "再乘",
    "然后",
    "接着",
)


def _is_multi_step(normalized: NormalizedQuestion) -> bool:
    """Conservatively detect chained multi-step questions for the agentic loop.

    Only fires on explicit chaining signals (二阶导 / 再求导 / 然后 ...) or 3+
    chained matrices, so single-step questions keep the fast deterministic path.
    """

    text = normalized.normalized_text
    if any(marker in text for marker in _MULTI_STEP_MARKERS):
        return True
    return text.count("[[") >= 3


def _read_image_bytes(path: str) -> bytes:
    return Path(path).read_bytes()


def _vision_prompt(normalized: NormalizedQuestion) -> str:
    return (
        "请描述图片中可直接看见的题面、机构、齿轮、齿数、标注和几何关系。"
        "不要解题，不要推导答案，不要补全看不清的信息。\n"
        f"题目文字：{normalized.normalized_text}\n"
        f"OCR文字：{normalized.ocr_text or '无'}"
    )
