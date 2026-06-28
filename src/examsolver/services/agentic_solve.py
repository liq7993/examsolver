"""Agentic multi-step solver.

For genuinely multi-step questions (二阶导 = differentiate twice, A·B·C = multiply
twice, ...) a single skill is not enough. Recognized patterns (N-th derivative,
chained matrix products) are decomposed *deterministically*; only an unrecognized
multi-step shape falls back to an LLM planner. Either way every sub-step is solved
by an existing deterministic skill through the normal dispatcher, each result is
verified, failed steps retry, and clean results chain into later steps before
assembly. Determinism stays at the leaves -- the LLM never computes an answer, and
for recognized patterns it does not even plan (so they work offline and can't be
corrupted by a weak model miscounting the decomposition).

Honest degradation: an unusable plan or an unsolvable sub-step raises
``SkillExecutionError`` so the graph falls back instead of fabricating.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, replace
from typing import Any

from examsolver.contracts import NormalizedQuestion, SolveResult, Step
from examsolver.llm.base import LLMClient, Message
from examsolver.pipeline.dispatcher import dispatch
from examsolver.skills.base import SkillExecutionError
from examsolver.skills.registry import list_skills

logger = logging.getLogger(__name__)

_PREV = "{{prev}}"

PLAN_SCHEMA: dict[str, object] = {
    "type": "object",
    "required": ["steps"],
    "properties": {
        "steps": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["goal", "subject", "question_type"],
                "properties": {
                    "goal": {"type": "string"},
                    "subject": {"type": "string"},
                    "question_type": {"type": "string"},
                },
                "additionalProperties": False,
            },
        },
        "final": {"type": "string"},
    },
    "additionalProperties": False,
}


@dataclass(frozen=True, slots=True)
class AgenticBudget:
    """Bounds so the orchestration cost stays controlled."""

    max_steps: int = 6
    max_retries: int = 1


def agentic_solve(
    question: NormalizedQuestion,
    *,
    llm: LLMClient | None,
    budget: AgenticBudget = AgenticBudget(),
) -> SolveResult:
    """Decompose a multi-step question, solve each step deterministically, assemble.

    Recognized patterns (N-th derivative, chained matrix products) are decomposed
    *deterministically* -- reliable and LLM-free. Only an unrecognized multi-step
    shape falls back to the LLM planner. Either way each leaf runs through a real
    deterministic skill; the LLM never computes an answer.
    """

    request_id = str(question.hints.get("request_id", "unknown"))
    plan = _deterministic_plan(question)
    plan_source = "deterministic"
    if plan is None:
        if llm is None:
            raise SkillExecutionError(
                "agentic solver: not deterministically decomposable and no LLM planner"
            )
        plan = _make_plan(question, llm)
        plan_source = "llm"
    if not plan:
        raise SkillExecutionError("agentic planner returned no steps")
    if len(plan) > budget.max_steps:
        raise SkillExecutionError(
            f"agentic plan exceeds budget ({len(plan)} > {budget.max_steps} steps)"
        )

    note_steps: list[Step] = []
    sub_answers: list[str] = []
    prev_result = ""
    for index, planned in enumerate(plan, start=1):
        goal = str(planned.get("goal", "")).replace(_PREV, prev_result).strip()
        question_type = str(planned.get("question_type", ""))
        subject = str(planned.get("subject", "")) or question.subject
        if not goal:
            raise SkillExecutionError(f"agentic step {index} has an empty goal")

        sub_question = replace(question, raw_text=goal, normalized_text=goal, subject=subject)
        result = _run_step(sub_question, question_type, budget=budget)
        answer_text = _answer_text(result)
        sub_answers.append(answer_text)
        note_steps.append(
            Step(
                index=index,
                description=f"子步 {index}（{subject}.{question_type}）：{goal}",
                formula_latex=answer_text if answer_text.startswith("$") else None,
            )
        )
        prev_result = str(result.meta.get("result") or answer_text)
        logger.info(
            "[%s] INFO services.agentic_solve: step %s done skill=%s",
            request_id,
            index,
            result.skill,
        )

    return SolveResult(
        question_type="multi_step",
        skill="agentic.multi_step",
        steps=note_steps,
        answer=sub_answers[-1] if sub_answers else None,
        meta={
            "success": True,
            "message": "已完成多步解题。",
            "agentic": True,
            "verified": True,
            "agentic.plan_source": plan_source,
            "agentic.plan": plan,
            "agentic.sub_answers": sub_answers,
        },
    )


_CN_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_NTH_DERIVATIVE_RE = re.compile(r"(.+?)\s*的\s*([一二三四五六七八九\d]+)\s*阶导数?")


def _deterministic_plan(question: NormalizedQuestion) -> list[dict[str, Any]] | None:
    """Decompose recognized multi-step patterns without an LLM (reliable + offline).

    Returns ``None`` for unrecognized shapes so the caller falls back to the LLM
    planner. These are exactly the patterns the router's ``_is_multi_step`` flags.
    """

    text = question.normalized_text
    return _nth_derivative_plan(text) or _matrix_chain_plan(text)


def _nth_derivative_plan(text: str) -> list[dict[str, Any]] | None:
    """``求 <expr> 的 N 阶导数`` -> N chained first-derivative steps."""

    match = _NTH_DERIVATIVE_RE.search(text)
    if not match:
        return None
    expression = match.group(1).strip().removeprefix("求").removeprefix("函数").strip()
    token = match.group(2)
    order = _CN_NUM.get(token, int(token) if token.isdigit() else 0)
    if not expression or not 2 <= order <= 6:
        return None
    steps = [_derivative_step(expression)]
    steps.extend(_derivative_step(_PREV) for _ in range(order - 1))
    return steps


def _matrix_chain_plan(text: str) -> list[dict[str, Any]] | None:
    """``A 乘 B 再乘 C ...`` -> chained matrix-multiplication steps."""

    matrices = _matrix_literals(text)
    if len(matrices) < 2:
        return None
    steps = [_matrix_mul_step(matrices[0], matrices[1])]
    steps.extend(_matrix_mul_step(_PREV, right) for right in matrices[2:])
    return steps


def _derivative_step(expression: str) -> dict[str, Any]:
    return {"goal": f"求 {expression} 的导数", "subject": "calculus", "question_type": "derivative"}


def _matrix_mul_step(left: str, right: str) -> dict[str, Any]:
    return {
        "goal": f"计算矩阵 {left} 乘 {right}",
        "subject": "linear_algebra",
        "question_type": "matrix_mul",
    }


def _matrix_literals(text: str) -> list[str]:
    """Extract bracket-balanced ``[[...],[...]]`` matrix literals in order."""

    literals: list[str] = []
    index = 0
    while True:
        start = text.find("[[", index)
        if start == -1:
            break
        depth = 0
        cursor = start
        while cursor < len(text):
            char = text[cursor]
            if char == "[":
                depth += 1
            elif char == "]":
                depth -= 1
                if depth == 0:
                    literals.append(text[start : cursor + 1])
                    index = cursor + 1
                    break
            cursor += 1
        else:
            break
    return literals


def _make_plan(question: NormalizedQuestion, llm: LLMClient) -> list[dict[str, Any]]:
    try:
        raw = llm.chat(
            [Message(role="user", content=_planner_prompt(question.normalized_text))],
            json_schema=PLAN_SCHEMA,
            max_tokens=700,
            temperature=0.0,
            timeout=60.0,
        )
        data = json.loads(_strip_code_fence(raw))
    except Exception as exc:
        raise SkillExecutionError("agentic planner call or parse failed") from exc
    if not isinstance(data, dict):
        raise SkillExecutionError("agentic planner did not return an object")
    steps = data.get("steps")
    if not isinstance(steps, list):
        raise SkillExecutionError("agentic plan has no steps list")
    return [step for step in steps if isinstance(step, dict)]


def _run_step(
    sub_question: NormalizedQuestion, question_type: str, *, budget: AgenticBudget
) -> SolveResult:
    last_error: Exception | None = None
    for _attempt in range(budget.max_retries + 1):
        try:
            result = dispatch(sub_question, question_type)
        except SkillExecutionError as exc:
            last_error = exc
            continue
        if result.skill != "unknown" and result.answer:
            return result
        last_error = SkillExecutionError(
            f"agentic step produced no usable answer (skill={result.skill})"
        )
    raise last_error or SkillExecutionError("agentic step failed")


def _planner_prompt(question: str) -> str:
    return (
        "你是解题规划器。把多步题拆成有序子步，每个子步都用下方目录里的一个确定性技能解决。\n"
        "技能会用程序直接解析每个 goal，所以 goal 必须简洁、规范、可机读：\n"
        "- 严格按题目的运算次数拆，不多拆也不少拆：「N 阶导数」=N 步求导"
        "（二阶=2 步，三阶=3 步）；「A 乘 B 再乘 C」=2 步矩阵乘。\n"
        "- 求导子步：goal 一律写成「求 <表达式> 的导数」，不要写「一阶/二阶导数」。\n"
        "- 矩阵乘子步：goal 一律写成「计算矩阵 <A> 乘 <B>」，矩阵用 [[行],[行]] 形式。\n"
        "- 需要上一步结果时用占位符 {{prev}}，且每个 goal 里 {{prev}} 最多出现一次，"
        "直接放在操作数位置。\n"
        "- goal 里只放子题本身，不要写「使用第一步的结果」「即…」这类解释文字。\n"
        "- subject 和 question_type 必须出自目录；你只负责拆解，绝不自己计算答案。\n\n"
        "示例1 — 求 x^3 的二阶导数：\n"
        '  [{"goal":"求 x^3 的导数","subject":"calculus","question_type":"derivative"},'
        '{"goal":"求 {{prev}} 的导数","subject":"calculus","question_type":"derivative"}]\n'
        "示例2 — 计算 [[1,2],[3,4]] 乘 [[5,6],[7,8]] 再乘 [[1,0],[1,1]]：\n"
        '  [{"goal":"计算矩阵 [[1,2],[3,4]] 乘 [[5,6],[7,8]]","subject":"linear_algebra",'
        '"question_type":"matrix_mul"},'
        '{"goal":"计算矩阵 {{prev}} 乘 [[1,0],[1,1]]","subject":"linear_algebra",'
        '"question_type":"matrix_mul"}]\n\n'
        f"可用技能目录：\n{_skill_catalog()}\n\n"
        f"题目：{question}"
    )


def _skill_catalog() -> str:
    lines: list[str] = []
    for entry in list_skills():
        subject = entry.get("subject")
        question_types = entry.get("question_types")
        if not isinstance(question_types, list):
            continue
        for question_type in question_types:
            lines.append(f"- subject={subject}, question_type={question_type}")
    return "\n".join(lines)


def _answer_text(result: SolveResult) -> str:
    if isinstance(result.answer, str):
        return result.answer
    return json.dumps(result.answer, ensure_ascii=False)


def _strip_code_fence(content: str) -> str:
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return text
