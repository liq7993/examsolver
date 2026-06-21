"""Calculus derivative skill (deterministic, sympy-backed).

Type-D skill per ARCHITECTURE.md: a deterministic solver built on sympy, not a
hand-rolled regex. It differentiates single-variable expressions (polynomials,
trig, exp/log, products/quotients, chain rule) exactly.

Honest degradation (ARCHITECTURE "诚实降级"): when the question contains no
expression sympy can parse, the skill raises ``SkillExecutionError`` so the
graph falls back to the general/unknown path instead of fabricating an answer.
"""

from __future__ import annotations

import re

import sympy as sp
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

from examsolver.contracts import NormalizedQuestion, SolveResult, Step, StudentExplanation
from examsolver.skills.base import SkillExecutionError

# convert_xor: ``^`` -> ``**``; implicit_multiplication_application: ``2x`` -> ``2*x``.
_TRANSFORMS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)
# Friendly names so ``e`` means Euler's number and ``pi`` means π.
_LOCAL_DICT: dict[str, object] = {"e": sp.E, "pi": sp.pi}

# Patterns that isolate the math expression from a natural-language question.
# Ordered most-specific first.
_EXPRESSION_PATTERNS = (
    r"对\s*(.+?)\s*求导",
    r"求\s*(.+?)\s*(?:对|关于)\s*[A-Za-z]",
    r"求\s*(.+?)\s*的导数",
    r"(?:derivative\s+of|d\s*/\s*d[A-Za-z])\s*(.+)",
    r"(.+?)\s*的导数",
)
_VARIABLE_PATTERN = re.compile(r"(?:对|关于)\s*([A-Za-z])\b")
_CJK_PATTERN = re.compile(r"[一-鿿]")
# A function definition like ``f(x)=...`` / ``函数 f(x)=...`` / ``s(t)=...`` names
# both the differentiation variable (the parenthesised symbol) and the expression
# (right of ``=``) -- the least ambiguous signal available. The expression capture
# admits only math characters and whitespace, so it stops at the first CJK run
# (e.g. a trailing ``的导数`` or ``求``).
_FUNCTION_DEF_PATTERN = re.compile(
    r"[A-Za-z]\s*\(\s*([A-Za-z])\s*\)\s*=\s*([A-Za-z0-9+\-*/^().\s]+)"
)


class DerivativeSkill:
    """Differentiate single-variable expressions deterministically via sympy."""

    name = "calculus.derivative"
    version = "0.2.0"
    subject = "calculus"
    question_types = ["derivative"]

    def can_handle(self, question: NormalizedQuestion) -> bool:
        text = _strip_latex_markers(question.normalized_text).lower()
        return any(key in text for key in ("导数", "求导", "derivative", "d/dx"))

    def solve(self, question: NormalizedQuestion) -> SolveResult:
        raw, variable_hint = _extract(question.normalized_text)
        expression = _safe_parse(raw)
        if expression is None:
            raise SkillExecutionError(
                "derivative skill cannot parse an expression from: "
                f"{question.normalized_text!r}"
            )

        variable = (
            sp.Symbol(variable_hint)
            if variable_hint
            else _detect_variable(question.normalized_text, expression)
        )
        derivative = sp.diff(expression, variable)

        expr_latex = sp.latex(expression)
        deriv_latex = sp.latex(derivative)
        var_latex = sp.latex(variable)
        operator = f"\\frac{{d}}{{d{var_latex}}}\\left({expr_latex}\\right)"
        answer = f"${operator} = {deriv_latex}$"

        return SolveResult(
            question_type="derivative",
            skill=self.name,
            steps=[
                Step(
                    index=1,
                    description="识别要求导的表达式与自变量",
                    formula_latex=f"{expr_latex},\\quad \\text{{变量}}={var_latex}",
                ),
                Step(
                    index=2,
                    description="对表达式套用求导法则（幂/链式/乘积/商法则）",
                    formula_latex=operator,
                ),
                Step(
                    index=3,
                    description="化简得到导数",
                    formula_latex=f"{operator} = {deriv_latex}",
                ),
            ],
            answer=answer,
            student_explanation=StudentExplanation(
                summary=f"这题是在求 ${expr_latex}$ 关于 ${var_latex}$ 的导数。",
                intuition=(
                    "导数刻画函数随自变量变化的瞬时变化率；遇到复合/乘积函数时，"
                    "按链式法则、乘积法则逐层展开即可。"
                ),
                step_by_step=[
                    f"先确认自变量是 ${var_latex}$。",
                    f"把 ${expr_latex}$ 按结构套用对应求导法则。",
                    f"化简后结果是 ${deriv_latex}$。",
                ],
                common_mistake=(
                    "常见错误：复合函数忘了乘内层导数（链式法则），"
                    "或乘积/商法则套用顺序写错。"
                ),
                self_check_question=(
                    f"你能把 ${var_latex}$ 代一个具体值，验证 ${deriv_latex}$ 是否合理吗？"
                ),
            ),
            meta={
                "success": True,
                "skill_version": self.version,
                "message": "已完成求导。",
                "calculus.derivative.expression": str(expression),
                "calculus.derivative.derivative": str(derivative),
                "calculus.derivative.variable": str(variable),
            },
        )


def _extract(text: str) -> tuple[str | None, str | None]:
    """Return ``(expression, variable_hint)`` for the question.

    A ``name(var)=expr`` function definition pins down both pieces unambiguously
    and takes priority; otherwise fall back to keyword patterns that yield only
    the expression (its variable is inferred later by ``_detect_variable``).
    """

    function_definition = _extract_function_definition(text)
    if function_definition is not None:
        return function_definition
    return _extract_expression(text), None


def _extract_function_definition(text: str) -> tuple[str, str] | None:
    """Pull ``(expression, variable)`` out of ``f(x)=...`` style questions.

    Covers ``求函数 f(x)=x^3-6x^2+9x 的导数`` and ``对 s(t)=2t^3-5t^2+3t 求 t 的导数``:
    the parenthesised symbol is the differentiation variable and the run right of
    ``=`` is the expression. Returning both together avoids the variable-vs-
    expression mix-up bare keyword patterns fall into -- which previously made
    ``对 s(t)=... 求 t 的导数`` resolve to a confident but wrong ``d/ds(t)=0``.
    """

    match = _FUNCTION_DEF_PATTERN.search(_strip_latex_markers(text))
    if not match:
        return None
    expression = match.group(2).strip().strip("：:，,。.")
    if not expression:
        return None
    return expression, match.group(1)


def _extract_expression(text: str) -> str | None:
    clean = _strip_latex_markers(text)
    for pattern in _EXPRESSION_PATTERNS:
        match = re.search(pattern, clean, flags=re.IGNORECASE)
        if match:
            candidate = match.group(1).strip().strip("：:，,。.")
            if candidate:
                return candidate
    return None


def _safe_parse(raw: str | None) -> sp.Expr | None:
    if not raw:
        return None
    # A candidate still carrying CJK characters is natural language, not a math
    # expression (e.g. "它", "这个函数"); decline so the graph falls back.
    if _CJK_PATTERN.search(raw):
        return None
    try:
        expr = parse_expr(raw, transformations=_TRANSFORMS, local_dict=_LOCAL_DICT)
    except Exception:
        return None
    # A bare number or a symbol-free constant is not a meaningful derivative target
    # coming from this path; but constants ARE valid (d/dx of 5 = 0). Reject only
    # parses that produced no usable sympy expression.
    if not isinstance(expr, sp.Expr):
        return None
    return expr


def _detect_variable(text: str, expression: sp.Expr) -> sp.Symbol:
    match = _VARIABLE_PATTERN.search(_strip_latex_markers(text))
    if match:
        return sp.Symbol(match.group(1))
    free_symbols = expression.free_symbols
    if len(free_symbols) == 1:
        only = next(iter(free_symbols))
        if isinstance(only, sp.Symbol):
            return only
    return sp.Symbol("x")


def _strip_latex_markers(text: str) -> str:
    return text.replace("$", "").replace("\\(", "").replace("\\)", "")
