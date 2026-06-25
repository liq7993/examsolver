import logging

from pytest import LogCaptureFixture

from examsolver.contracts import NormalizedQuestion, NoteEntry, SolveRequest, SolveResult, Step
from examsolver.graph.nodes import (
    _normalized_with_multimodal_context,
    format_node,
    normalize_node,
    persist_node,
)
from examsolver.pipeline.classifier import classify
from examsolver.storage.history_repo import get_response


def test_normalize_node_writes_normalized_and_logs_lifecycle(
    caplog: LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="examsolver.graph.nodes")

    state = normalize_node({"request": SolveRequest(question="求 x^2 对 x 的导数")})

    assert state["normalized"].subject == "calculus"
    messages = [record.getMessage() for record in caplog.records]
    assert any("graph.nodes.normalize_node: begin" in message for message in messages)
    assert any("graph.nodes.normalize_node: done" in message for message in messages)


def test_format_node_writes_response_and_logs_lifecycle(caplog: LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="examsolver.graph.nodes")
    normalized = _normalized()
    result = _result()

    state = format_node({"normalized": normalized, "solve_result": result})

    assert state["response"].solve_id == "solve-1"
    assert state["response"].steps == ["识别表达式：$x^2$"]
    messages = [record.getMessage() for record in caplog.records]
    assert any("graph.nodes.format_node: begin" in message for message in messages)
    assert any("graph.nodes.format_node: done" in message for message in messages)


def test_format_node_attaches_note_when_present() -> None:
    normalized = _normalized()
    note = NoteEntry(
        solve_id="solve-1",
        title="求导",
        question_latex=normalized.normalized_text,
        steps=_result().steps,
        answer="2x",
        student_explanation=None,
        common_mistakes=[],
        related_formulas=[],
        flashcards=[],
        citations=[],
        subject="calculus",
        question_type="derivative",
    )

    state = format_node({"normalized": normalized, "solve_result": _result(), "note": note})

    assert state["response"].note == note


def test_persist_node_saves_response_and_logs_lifecycle(caplog: LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="examsolver.graph.nodes")
    normalized = _normalized()
    response = format_node({"normalized": normalized, "solve_result": _result()})["response"]

    state = persist_node({"normalized": normalized, "response": response})

    assert state == {}
    stored = get_response("solve-1")
    assert stored is not None
    assert stored.answer == "2x"
    messages = [record.getMessage() for record in caplog.records]
    assert any("graph.nodes.persist_node: begin" in message for message in messages)
    assert any("graph.nodes.persist_node: done" in message for message in messages)


def test_multimodal_context_folds_ocr_into_unclassifiable_question() -> None:
    typed = NormalizedQuestion(
        raw_text="计算",
        normalized_text="计算",
        subject="unknown",
        hints={"request_id": "rid", "solve_id": "sid", "created_at": "2026-06-24"},
    )

    enriched = _normalized_with_multimodal_context(
        {"normalized": typed, "ocr_text": "求 x^2 对 x 的导数"}
    )

    assert "求 x^2 对 x 的导数" in enriched.normalized_text
    assert enriched.subject == "calculus"
    assert classify(enriched) == "derivative"


def test_multimodal_context_leaves_clear_typed_question_untouched() -> None:
    typed = _normalized()  # already classifiable on its own

    enriched = _normalized_with_multimodal_context(
        {"normalized": typed, "ocr_text": "无关 OCR 噪声"}
    )

    assert enriched.normalized_text == "求 x^2 对 x 的导数"
    assert enriched.ocr_text == "无关 OCR 噪声"


def _normalized() -> NormalizedQuestion:
    return NormalizedQuestion(
        raw_text="求 x^2 对 x 的导数",
        normalized_text="求 x^2 对 x 的导数",
        subject="calculus",
        hints={"request_id": "rid-1", "solve_id": "solve-1", "created_at": "2026-05-20"},
    )


def _result() -> SolveResult:
    return SolveResult(
        question_type="derivative",
        skill="calculus.derivative",
        steps=[Step(index=1, description="识别表达式", formula_latex="x^2")],
        answer="2x",
        meta={"success": True, "message": "ok"},
    )
