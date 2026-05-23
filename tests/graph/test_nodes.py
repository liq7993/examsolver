import logging

from examsolver.contracts import NormalizedQuestion, SolveRequest, SolveResult, Step
from examsolver.graph.nodes import format_node, normalize_node, persist_node
from examsolver.storage.history_repo import get_response


def test_normalize_node_writes_normalized_and_logs_lifecycle(caplog) -> None:
    caplog.set_level(logging.INFO, logger="examsolver.graph.nodes")

    state = normalize_node({"request": SolveRequest(question="求 x^2 对 x 的导数")})

    assert state["normalized"].subject == "calculus"
    messages = [record.getMessage() for record in caplog.records]
    assert any("graph.normalize_node: begin" in message for message in messages)
    assert any("graph.normalize_node: done" in message for message in messages)


def test_format_node_writes_response_and_logs_lifecycle(caplog) -> None:
    caplog.set_level(logging.INFO, logger="examsolver.graph.nodes")
    normalized = _normalized()
    result = _result()

    state = format_node({"normalized": normalized, "solve_result": result})

    assert state["response"].solve_id == "solve-1"
    assert state["response"].steps == ["识别表达式：$x^2$"]
    messages = [record.getMessage() for record in caplog.records]
    assert any("graph.format_node: begin" in message for message in messages)
    assert any("graph.format_node: done" in message for message in messages)


def test_persist_node_saves_response_and_logs_lifecycle(caplog) -> None:
    caplog.set_level(logging.INFO, logger="examsolver.graph.nodes")
    normalized = _normalized()
    response = format_node({"normalized": normalized, "solve_result": _result()})["response"]

    state = persist_node({"normalized": normalized, "response": response})

    assert state == {}
    stored = get_response("solve-1")
    assert stored is not None
    assert stored.answer == "2x"
    messages = [record.getMessage() for record in caplog.records]
    assert any("graph.persist_node: begin" in message for message in messages)
    assert any("graph.persist_node: done" in message for message in messages)


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
