import pytest

from examsolver.contracts import NormalizedQuestion, SolveRequest, SolveResult, Step, StudentExplanation
from examsolver.graph import build_graph, run_solve_graph
from examsolver.graph.nodes import (
    explanation_enhancer_node,
    note_builder_node,
    normalize_node,
    route_after_router,
    router_agent_node,
)
from examsolver.storage.history_repo import get_response, list_history


def test_build_graph_compiles_once() -> None:
    assert build_graph() is build_graph()


def test_normalize_node_carries_image_paths_and_subject_hint() -> None:
    state = normalize_node(
        {
            "request": SolveRequest(
                question="求 x^2 对 x 的导数",
                subject_hint="calculus",
                image_paths=["/tmp/q.png"],
            )
        }
    )

    normalized = state["normalized"]
    assert normalized.subject == "calculus"
    assert normalized.has_image is True
    assert normalized.image_paths == ["/tmp/q.png"]
    assert normalized.hints["image_count"] == 1


def test_router_routes_unknown_to_general_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("examsolver.graph.router_agent.pick_llm", lambda *_args, **_kwargs: None)

    state = router_agent_node(
        {
            "normalized": NormalizedQuestion(
                raw_text="解释一下天气",
                normalized_text="解释一下天气",
                subject="unknown",
            )
        }
    )

    assert state["question_type"] == "unknown"
    assert state["subject"] == "general"
    assert state["routing_confidence"] == 0.0
    assert "No LLM router is configured" in state["routing_reasoning"]
    assert state["fallback_reasons"] == ["llm_router_unavailable"]
    assert route_after_router(state) == "general"


def test_note_builder_preserves_structured_steps() -> None:
    result = SolveResult(
        question_type="derivative",
        skill="calculus.derivative",
        steps=[Step(index=1, description="识别表达式", formula_latex="x^2")],
        answer="2x",
        student_explanation=StudentExplanation(
            summary="summary",
            intuition="intuition",
            step_by_step=[],
            common_mistake="漏乘指数",
            self_check_question="check?",
        ),
        meta={"success": True},
    )

    state = note_builder_node(
        {
            "normalized": NormalizedQuestion(
                raw_text="求导",
                normalized_text="求导",
                subject="calculus",
                hints={"solve_id": "abc"},
            ),
            "solve_result": result,
        }
    )

    note = state["note"]
    assert note.solve_id == "abc"
    assert note.steps == result.steps
    assert note.common_mistakes == []


def test_explanation_enhancer_node_skips_when_explanation_exists() -> None:
    result = SolveResult(
        question_type="derivative",
        skill="calculus.derivative",
        steps=[],
        answer="2x",
        student_explanation=StudentExplanation(
            summary="summary",
            intuition="intuition",
            step_by_step=[],
            common_mistake="",
            self_check_question="check?",
        ),
    )

    state = explanation_enhancer_node(
        {
            "normalized": NormalizedQuestion(
                raw_text="求导",
                normalized_text="求导",
                subject="calculus",
                hints={"request_id": "rid-1"},
            ),
            "solve_result": result,
        }
    )

    assert state == {}


def test_run_solve_graph_matches_existing_service_contract() -> None:
    response = run_solve_graph(SolveRequest(question="求 x^2 对 x 的导数"))

    assert response.success is True
    assert response.subject == "calculus"
    assert response.question_type == "derivative"
    assert response.skill == "calculus.derivative"
    assert response.answer == "$\\frac{d}{dx}(x^2) = 2x$"
    assert response.note is not None
    assert response.note.solve_id == response.solve_id

    stored = get_response(response.solve_id)
    assert stored is not None
    assert stored.answer == response.answer
    assert stored.note is not None
    assert stored.note.solve_id == response.solve_id


def test_run_solve_graph_unknown_uses_general_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("examsolver.graph.router_agent.pick_llm", lambda *_args, **_kwargs: None)

    response = run_solve_graph(SolveRequest(question="解释一下今天的天气"))

    assert response.success is False
    assert response.subject == "general"
    assert response.question_type == "unknown"
    assert response.skill == "unknown"
    assert response.fallback_reasons == ["llm_router_unavailable"]

    page = list_history()
    assert len(page.items) == 1
    assert page.items[0].success is False
