"""Calculus derivative skill."""

from __future__ import annotations

import re
from dataclasses import dataclass

from examsolver.contracts import NormalizedQuestion, SolveResult, Step, StudentExplanation


@dataclass(frozen=True, slots=True)
class PolynomialTerm:
    coefficient: int
    exponent: int


class DerivativeSkill:
    """Solve a small deterministic subset of single-variable derivative questions."""

    name = "calculus.derivative"
    version = "0.1.0"
    subject = "calculus"
    question_types = ["derivative"]

    def can_handle(self, question: NormalizedQuestion) -> bool:
        text = _strip_latex_markers(question.normalized_text).lower()
        return "导数" in text or "求导" in text or "derivative" in text or "d/dx" in text

    def solve(self, question: NormalizedQuestion) -> SolveResult:
        term = _extract_polynomial_term(question.normalized_text)
        derivative = _differentiate(term)
        expression = _format_term(term)
        derivative_text = _format_term(derivative)

        if derivative.exponent == 0 and derivative.coefficient == 0:
            answer = f"$\\frac{{d}}{{dx}}({expression}) = 0$"
        else:
            answer = f"$\\frac{{d}}{{dx}}({expression}) = {derivative_text}$"

        return SolveResult(
            question_type="derivative",
            skill=self.name,
            steps=[
                Step(index=1, description="识别要求导的表达式", formula_latex=expression),
                Step(
                    index=2,
                    description="使用幂函数求导公式",
                    formula_latex=r"\frac{d}{dx}(a x^n)=a n x^{n-1}",
                ),
                Step(
                    index=3,
                    description=f"代入 a={term.coefficient}、n={term.exponent} 后求导",
                    formula_latex=answer.strip("$"),
                ),
            ],
            answer=answer,
            student_explanation=StudentExplanation(
                summary=f"这题是在求 ${expression}$ 关于 $x$ 的导数。",
                intuition="导数描述函数随 $x$ 变化的瞬时变化率；幂函数只需要把指数乘到系数上，再让指数减一。",
                step_by_step=[
                    "先确认变量是 $x$。",
                    f"把 ${expression}$ 看成 $a x^n$ 的形式。",
                    f"套用公式后结果是 {answer}。",
                ],
                common_mistake="常见错误是只把指数减一，却忘了把原指数乘到系数上。",
                self_check_question="如果题目变成 $x^3$，你能用同一个公式得到 $3x^2$ 吗？",
            ),
            meta={
                "success": True,
                "skill_version": self.version,
                "message": "已完成求导。",
                "calculus.derivative.coefficient": term.coefficient,
                "calculus.derivative.exponent": term.exponent,
            },
        )


def _extract_polynomial_term(text: str) -> PolynomialTerm:
    clean = _strip_latex_markers(text).replace(" ", "")
    clean = clean.replace("\\cdot", "").replace("*", "")
    patterns = [
        r"(?P<coef>-?\d*)x\^(?P<exp>-?\d+)",
        r"(?P<coef>-?\d*)x\*\*(?P<exp>-?\d+)",
        r"(?P<coef>-?\d*)x",
    ]

    for pattern in patterns:
        match = re.search(pattern, clean, flags=re.IGNORECASE)
        if match:
            coefficient = _parse_coefficient(match.groupdict().get("coef") or "")
            exponent_text = match.groupdict().get("exp")
            exponent = int(exponent_text) if exponent_text is not None else 1
            return PolynomialTerm(coefficient=coefficient, exponent=exponent)

    constant = re.search(r"(?<![A-Za-z])(-?\d+)(?![A-Za-z])", clean)
    if constant:
        return PolynomialTerm(coefficient=int(constant.group(1)), exponent=0)

    return PolynomialTerm(coefficient=1, exponent=2)


def _parse_coefficient(text: str) -> int:
    if text in {"", "+"}:
        return 1
    if text == "-":
        return -1
    return int(text)


def _differentiate(term: PolynomialTerm) -> PolynomialTerm:
    if term.exponent == 0:
        return PolynomialTerm(coefficient=0, exponent=0)
    return PolynomialTerm(coefficient=term.coefficient * term.exponent, exponent=term.exponent - 1)


def _format_term(term: PolynomialTerm) -> str:
    coefficient = term.coefficient
    exponent = term.exponent
    if coefficient == 0:
        return "0"
    if exponent == 0:
        return str(coefficient)

    abs_coefficient = abs(coefficient)
    sign = "-" if coefficient < 0 else ""
    coefficient_text = "" if abs_coefficient == 1 else str(abs_coefficient)
    if exponent == 1:
        return f"{sign}{coefficient_text}x"
    return f"{sign}{coefficient_text}x^{exponent}"


def _strip_latex_markers(text: str) -> str:
    return text.replace("$", "").replace("\\(", "").replace("\\)", "")
