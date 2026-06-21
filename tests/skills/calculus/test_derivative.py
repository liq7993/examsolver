import pytest

from examsolver.contracts import SolveRequest, Step
from examsolver.pipeline.normalizer import normalize
from examsolver.skills.base import SkillExecutionError
from examsolver.skills.calculus import DerivativeSkill


def test_derivative_skill_solves_power_rule() -> None:
    question = normalize(SolveRequest(question="求 x^2 对 x 的导数"))
    result = DerivativeSkill().solve(question)

    assert result.skill == "calculus.derivative"
    assert all(isinstance(step, Step) for step in result.steps)
    assert result.answer == "$\\frac{d}{dx}\\left(x^{2}\\right) = 2 x$"
    assert result.student_explanation is not None


def test_derivative_skill_solves_coefficient_power() -> None:
    question = normalize(SolveRequest(question="求 3x^3 的导数"))
    result = DerivativeSkill().solve(question)

    assert result.answer == "$\\frac{d}{dx}\\left(3 x^{3}\\right) = 9 x^{2}$"


def test_derivative_skill_solves_trig_via_sympy() -> None:
    # The old regex implementation silently mis-read sin(x) as x and returned 1.
    # sympy differentiates it correctly to cos(x).
    question = normalize(SolveRequest(question="求 sin(x) 对 x 的导数"))
    result = DerivativeSkill().solve(question)

    assert isinstance(result.answer, str)
    assert "\\cos" in result.answer
    assert result.answer == (
        "$\\frac{d}{dx}\\left(\\sin{\\left(x \\right)}\\right) = \\cos{\\left(x \\right)}$"
    )


def test_derivative_skill_applies_product_rule() -> None:
    question = normalize(SolveRequest(question="对 x*sin(x) 求导"))
    result = DerivativeSkill().solve(question)

    # d/dx[x*sin(x)] = x*cos(x) + sin(x)
    assert isinstance(result.answer, str)
    assert "\\cos" in result.answer
    assert "\\sin" in result.answer


def test_derivative_skill_parses_function_definition_notation() -> None:
    # ``函数 f(x)=...`` previously left CJK in the captured expression and was
    # rejected; the function-definition path now strips the ``f(x)=`` wrapper.
    question = normalize(SolveRequest(question="求函数 f(x)=x^3-6x^2+9x 的导数"))
    result = DerivativeSkill().solve(question)

    assert result.answer == (
        "$\\frac{d}{dx}\\left(x^{3} - 6 x^{2} + 9 x\\right) = 3 x^{2} - 12 x + 9$"
    )


def test_derivative_skill_uses_parenthesised_variable_not_a_trailing_letter() -> None:
    # Regression: ``对 s(t)=... 求 t 的导数`` used to mis-read the expression as
    # ``t`` and the variable as ``s``, returning a confident but wrong d/ds(t)=0.
    # The function-definition path pins the variable to ``t`` and the expression
    # to the run right of ``=``.
    question = normalize(SolveRequest(question="对 s(t)=2t^3-5t^2+3t 求 t 的导数"))
    result = DerivativeSkill().solve(question)

    assert result.answer == (
        "$\\frac{d}{dt}\\left(2 t^{3} - 5 t^{2} + 3 t\\right) = 6 t^{2} - 10 t + 3$"
    )


def test_derivative_skill_declines_when_no_expression() -> None:
    # Honest degradation: no parseable expression -> raise so the graph falls back
    # to the general/unknown path instead of fabricating an answer.
    question = normalize(SolveRequest(question="这道题图里有个齿轮，求它的导数"))
    with pytest.raises(SkillExecutionError):
        DerivativeSkill().solve(question)
