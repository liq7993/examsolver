"""Shared graph state for one solve invocation."""

from __future__ import annotations

from typing import Any, TypedDict

from examsolver.contracts import (
    ExplanationEnhancer,
    NormalizedQuestion,
    NoteEntry,
    SolveRequest,
    SolveResponse,
    SolveResult,
)


class SolveState(TypedDict, total=False):
    """State carried through the LangGraph solve graph.

    The broad field set mirrors ARCHITECTURE.md section 2.3 so future OCR, VLM,
    RAG, and note-building nodes can be added without changing the central state
    contract. Some compatibility fields are kept for the current graph wrapper.
    """

    # Compatibility inputs used by the current graph runner.
    request: SolveRequest
    enhancer: ExplanationEnhancer

    # Architecture 2.3 input fields.
    request_id: str
    raw_question: str
    image_paths: list[str]
    user_subject_hint: str | None

    # Multimodal outputs.
    ocr_text: str
    ocr_bboxes: list[dict[str, Any]]
    vision_description: str
    needs_vision: bool

    # Normalization output.
    normalized: NormalizedQuestion

    # Routing output.
    subject: str
    question_type: str
    routing_confidence: float
    routing_reasoning: str

    # RAG output.
    retrieved_chunks: list[Any]

    # Solve and note outputs.
    solve_result: SolveResult
    note: NoteEntry

    # Final output and metadata.
    response: SolveResponse
    errors: list[str]
    fallback_reasons: list[str]

    # Current persistence wrapper detail.
    persistence_error: str


SolveGraphState = SolveState
