from examsolver.contracts import SolveRequest
from examsolver.graph import run_solve_graph


def test_multi_step_question_routes_to_agentic_and_chains() -> None:
    # 二阶导 is a recognized pattern -> deterministic decomposition, no LLM needed,
    # so this runs end-to-end offline through the real compiled graph.
    response = run_solve_graph(SolveRequest(question="求 x^3 的二阶导数"))

    assert response.success is True
    assert response.question_type == "multi_step"
    assert response.skill == "agentic.multi_step"
    assert "6 x" in str(response.answer)
    assert "agentic_failed" not in response.fallback_reasons


def test_single_step_question_keeps_the_fast_deterministic_path() -> None:
    response = run_solve_graph(SolveRequest(question="求 x^2 对 x 的导数"))

    # The conservative multi-step trigger must not capture ordinary single-step
    # questions -- they stay on the direct skill path, no LLM planner involved.
    assert response.question_type == "derivative"
    assert response.skill == "calculus.derivative"
    assert response.answer == "$\\frac{d}{dx}\\left(x^{2}\\right) = 2 x$"
