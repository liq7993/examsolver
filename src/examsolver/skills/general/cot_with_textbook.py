"""General Type-L chain-of-thought style fallback skill."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from examsolver.contracts import NormalizedQuestion, SolveResult, Step, StudentExplanation
from examsolver.llm.base import LLMClient, Message
from examsolver.skills.base import SkillExecutionError

COT_SCHEMA: dict[str, object] = {
    "type": "object",
    "required": ["thinking", "steps", "answer", "common_mistakes"],
    "properties": {
        "thinking": {"type": "string"},
        "steps": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["description"],
                "properties": {
                    "description": {"type": "string"},
                    "formula_latex": {"type": ["string", "null"]},
                },
                "additionalProperties": False,
            },
        },
        "answer": {"type": "string"},
        "common_mistakes": {
            "type": "array",
            "minItems": 1,
            "items": {"type": "string"},
        },
    },
    "additionalProperties": False,
}
_PROMPT_PATH = Path(__file__).with_name("prompts") / "cot_with_textbook.zh.md"


class CotWithTextbookSkill:
    """LLM-only general fallback for unsupported or open-ended questions."""

    name = "general.cot_with_textbook"
    version = "0.1.0"
    subject = "general"
    question_types = ["unknown", "general"]
    skill_type = "llm"
    needs_vision = False
    needs_rag = False

    def can_handle(self, question: NormalizedQuestion) -> bool:
        _ = question
        return True

    def solve(self, question: NormalizedQuestion, *, llm: LLMClient | None = None) -> SolveResult:
        if llm is None:
            raise SkillExecutionError("general.cot_with_textbook requires an LLM client")

        messages = [
            Message(role="system", content=_prompt()),
            Message(role="user", content=question.normalized_text),
        ]
        try:
            raw = llm.chat(messages, json_schema=COT_SCHEMA, max_tokens=1500, temperature=0.2)
            parsed = _parse_response(raw)
        except Exception as exc:
            raise SkillExecutionError("general.cot_with_textbook LLM call failed") from exc

        steps = [
            Step(
                index=index + 1,
                description=step["description"],
                formula_latex=step.get("formula_latex"),
            )
            for index, step in enumerate(parsed["steps"])
        ]
        common_mistakes = parsed["common_mistakes"]
        return SolveResult(
            question_type="unknown",
            skill=self.name,
            steps=steps,
            answer=parsed["answer"],
            student_explanation=StudentExplanation(
                summary=parsed["thinking"],
                intuition="先把题目归纳成可解释的核心概念，再按考试答题结构展开。",
                step_by_step=[_step_to_text(step) for step in steps],
                common_mistake=common_mistakes[0],
                self_check_question="我的答案是否同时说明了概念、作用和适用条件？",
            ),
            meta={
                "success": True,
                "skill_version": self.version,
                "message": "已完成通用结构化解答。",
                "general.cot_with_textbook.thinking": parsed["thinking"],
                "general.cot_with_textbook.common_mistakes": common_mistakes,
                "common_mistakes": common_mistakes,
            },
        )


def _prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


def _parse_response(raw: str) -> dict[str, Any]:
    data = json.loads(_strip_code_fence(raw))
    if not isinstance(data, dict):
        raise ValueError("general COT response must be a JSON object")
    steps = data.get("steps")
    common_mistakes = data.get("common_mistakes")
    if not isinstance(data.get("thinking"), str) or not data["thinking"]:
        raise ValueError("thinking must be a non-empty string")
    if not isinstance(data.get("answer"), str) or not data["answer"]:
        raise ValueError("answer must be a non-empty string")
    if not isinstance(steps, list) or not steps:
        raise ValueError("steps must be a non-empty array")
    if not isinstance(common_mistakes, list) or not common_mistakes:
        raise ValueError("common_mistakes must be a non-empty array")
    parsed_steps = [_parse_step(step) for step in steps]
    parsed_mistakes = [mistake for mistake in common_mistakes if isinstance(mistake, str) and mistake]
    if not parsed_mistakes:
        raise ValueError("common_mistakes must contain strings")
    return {
        "thinking": data["thinking"],
        "steps": parsed_steps,
        "answer": data["answer"],
        "common_mistakes": parsed_mistakes,
    }


def _parse_step(value: object) -> dict[str, str | None]:
    if not isinstance(value, dict):
        raise ValueError("each step must be an object")
    step = cast(dict[str, object], value)
    description = step.get("description")
    formula_latex = step.get("formula_latex")
    if not isinstance(description, str) or not description:
        raise ValueError("step.description must be a non-empty string")
    if formula_latex is not None and not isinstance(formula_latex, str):
        raise ValueError("step.formula_latex must be a string or null")
    return {"description": description, "formula_latex": formula_latex}


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


def _step_to_text(step: Step) -> str:
    if step.formula_latex:
        return f"{step.description}：${step.formula_latex}$"
    return step.description

