import json
from pathlib import Path
from typing import Any, cast

import pytest

from examsolver.contracts import NormalizedQuestion, SolveRequest, SolveResult, StudentExplanation
from examsolver.services.solve_service import solve
from examsolver.storage.history_repo import get_response, list_history

FORCE_FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "force_balance_regression.json"


def _force_cases() -> list[dict[str, Any]]:
    return cast(list[dict[str, Any]], json.loads(FORCE_FIXTURE_PATH.read_text(encoding="utf-8")))


class FakeEnhancer:
    name = "fake"
    version = "0.1.0"

    def enhance(
        self,
        question: NormalizedQuestion,
        result: SolveResult,
    ) -> StudentExplanation:
        return StudentExplanation(
            summary=f"Gemma explanation for {question.raw_text}",
            intuition="Use the deterministic result as the source of truth.",
            step_by_step=["The enhancer only fills the teaching explanation."],
            common_mistake="Do not replace deterministic answer fields.",
            self_check_question="Did the original skill output stay unchanged?",
        )


def test_solve_service_returns_derivative_response() -> None:
    response = solve(SolveRequest(question="求 x^2 对 x 的导数"))

    assert response.success is True
    assert len(response.solve_id) == 32
    assert response.subject == "calculus"
    assert response.question_type == "derivative"
    assert response.skill == "calculus.derivative"
    assert response.answer == "$\\frac{d}{dx}(x^2) = 2x$"

    stored = get_response(response.solve_id)
    assert stored is not None
    assert stored.answer == response.answer


def test_solve_service_unknown_is_not_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("examsolver.graph.router_agent.pick_llm", lambda *_args, **_kwargs: None)

    response = solve(SolveRequest(question="解释一下今天的天气"))

    assert response.success is False
    assert response.subject == "general"
    assert response.question_type == "unknown"
    assert response.skill == "unknown"
    assert response.message == "当前版本尚未支持此题型。"
    assert response.fallback_reasons == ["llm_router_unavailable"]

    page = list_history()
    assert len(page.items) == 1
    assert page.items[0].success is False


def test_solve_service_can_use_optional_explanation_enhancer_for_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("examsolver.graph.router_agent.pick_llm", lambda *_args, **_kwargs: None)

    response = solve(SolveRequest(question="解释一下今天的天气"), enhancer=FakeEnhancer())

    assert response.success is False
    assert response.question_type == "unknown"
    assert response.skill == "unknown"
    assert response.answer is None
    assert response.student_explanation is not None
    assert response.student_explanation.summary == "Gemma explanation for 解释一下今天的天气"


def test_solve_service_returns_matrix_mul_response() -> None:
    response = solve(SolveRequest(question="计算矩阵 [[1,2],[3,4]] 乘 [[5,6],[7,8]]"))

    assert response.success is True
    assert response.subject == "linear_algebra"
    assert response.question_type == "matrix_mul"
    assert response.skill == "linear_algebra.matrix_mul"
    assert response.answer == "$\\begin{bmatrix} 19 & 22 \\\\ 43 & 50 \\end{bmatrix}$"


def test_solve_service_returns_force_balance_response() -> None:
    response = solve(SolveRequest(question="一个 10 N 的力向右作用，求它的平衡力。"))

    assert response.success is True
    assert response.subject == "mechanics"
    assert response.question_type == "force_balance"
    assert response.skill == "mechanics.force_balance"
    assert response.answer == "$10\\,\\mathrm{N}$，方向向左"

    stored = get_response(response.solve_id)
    assert stored is not None
    assert stored.question_type == "force_balance"


@pytest.mark.parametrize("case", _force_cases(), ids=lambda case: str(case["name"]))
def test_solve_service_force_balance_regression_cases(case: dict[str, Any]) -> None:
    response = solve(SolveRequest(question=str(case["question"])))

    assert response.success is True
    assert response.subject == case["expected_subject"]
    assert response.question_type == case["expected_question_type"]
    assert response.skill == case["expected_skill"]
    assert case["expected_answer_contains"] in str(response.answer)

    page = list_history()
    assert len(page.items) == 1
    assert page.items[0].solve_id == response.solve_id
    assert page.items[0].subject == "mechanics"


def test_solve_service_force_balance_unsupported_case_falls_back_to_unknown() -> None:
    response = solve(
        SolveRequest(question="检查 10 N 向右、10 N 向左、5 N 向上、5 N 向下是否平衡。")
    )

    assert response.success is False
    assert response.subject == "mechanics"
    assert response.question_type == "unknown"
    assert response.skill == "unknown"

    page = list_history()
    assert len(page.items) == 1
    assert page.items[0].subject == "mechanics"
    assert page.items[0].success is False
