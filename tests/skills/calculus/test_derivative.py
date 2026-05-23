from examsolver.contracts import SolveRequest, Step
from examsolver.pipeline.normalizer import normalize
from examsolver.skills.calculus import DerivativeSkill


def test_derivative_skill_solves_power_rule() -> None:
    question = normalize(SolveRequest(question="求 x^2 对 x 的导数"))
    result = DerivativeSkill().solve(question)

    assert result.skill == "calculus.derivative"
    assert all(isinstance(step, Step) for step in result.steps)
    assert result.answer == "$\\frac{d}{dx}(x^2) = 2x$"
    assert result.student_explanation is not None


def test_derivative_skill_solves_coefficient_power() -> None:
    question = normalize(SolveRequest(question="求 3x^3 的导数"))
    result = DerivativeSkill().solve(question)

    assert result.answer == "$\\frac{d}{dx}(3x^3) = 9x^2$"
