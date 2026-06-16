"""Mechanism gear-train hybrid skill."""

from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path
from typing import Any

from examsolver.contracts import NormalizedQuestion, SolveResult, Step, StudentExplanation
from examsolver.llm.base import LLMClient, Message
from examsolver.skills.base import SkillExecutionError

EXTRACT_SCHEMA: dict[str, object] = {
    "type": "object",
    "required": ["stages"],
    "properties": {
        "stages": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["driving_teeth", "driven_teeth"],
                "properties": {
                    "driving_teeth": {"type": "integer", "minimum": 1},
                    "driven_teeth": {"type": "integer", "minimum": 1},
                },
                "additionalProperties": False,
            },
        }
    },
    "additionalProperties": False,
}
_PROMPT_PATH = Path(__file__).with_name("prompts") / "gear_train_extract.zh.md"


class GearTrainSkill:
    """Hybrid VLM/LLM extraction plus deterministic transmission-ratio calculation."""

    name = "mechanism.gear_train"
    version = "0.1.0"
    subject = "mechanism"
    question_types = ["gear_train"]
    skill_type = "hybrid"
    needs_vision = True
    needs_rag = False
    requires_llm = True

    def can_handle(self, question: NormalizedQuestion) -> bool:
        text = _context_text(question).lower()
        return any(keyword in text for keyword in ("齿轮", "传动比", "齿数", "gear", "z1", "z2"))

    def solve(
        self,
        question: NormalizedQuestion,
        *,
        llm: LLMClient | None = None,
    ) -> SolveResult:
        if llm is None:
            raise SkillExecutionError("mechanism.gear_train requires an LLM extractor")

        stages = _extract_stages(question, llm=llm)
        if not stages:
            raise SkillExecutionError("mechanism.gear_train could not extract gear teeth")

        ratio = Fraction(1, 1)
        steps: list[Step] = []
        for index, stage in enumerate(stages, start=1):
            stage_ratio = Fraction(stage["driven_teeth"], stage["driving_teeth"])
            ratio *= stage_ratio
            steps.append(_stage_step(index, stage, stage_ratio))
        steps.append(
            Step(
                index=len(stages) + 1,
                description="将各级传动比相乘得到总传动比",
                formula_latex=rf"i=\prod i_k={_fraction_latex(ratio)}={_format_number(ratio)}",
            )
        )

        return SolveResult(
            question_type="gear_train",
            skill=self.name,
            skill_version=self.version,
            steps=steps,
            answer=f"总传动比 i = {_format_number(ratio)}",
            student_explanation=_explanation(ratio, len(stages)),
            meta={
                "success": True,
                "skill_version": self.version,
                "message": "已完成齿轮传动比计算。",
                "mechanism.gear_train.ratio": float(ratio),
                "mechanism.gear_train.ratio_fraction": f"{ratio.numerator}/{ratio.denominator}",
                "mechanism.gear_train.stages_count": len(stages),
                "mechanism.gear_train.stages": stages,
                "common_mistakes": [
                    "不要把主动轮和从动轮齿数倒置；单级传动比按从动轮齿数除以主动轮齿数。",
                    "多级传动要逐级相乘，不能只取最后一级齿数比。",
                ],
            },
        )


def _extract_stages(question: NormalizedQuestion, *, llm: LLMClient) -> list[dict[str, int]]:
    try:
        raw = llm.chat(
            [
                Message(role="system", content=_prompt()),
                Message(role="user", content=_context_text(question)),
            ],
            json_schema=EXTRACT_SCHEMA,
            max_tokens=512,
            temperature=0.0,
        )
        payload = json.loads(_strip_code_fence(raw))
    except Exception as exc:
        raise SkillExecutionError("mechanism.gear_train LLM extraction failed") from exc
    if not isinstance(payload, dict):
        raise SkillExecutionError("mechanism.gear_train extraction must be a JSON object")
    return _validate_stages(payload)


def _validate_stages(payload: dict[str, Any]) -> list[dict[str, int]]:
    stages = payload.get("stages")
    if not isinstance(stages, list):
        raise SkillExecutionError("mechanism.gear_train stages must be a list")
    parsed: list[dict[str, int]] = []
    for stage in stages:
        if not isinstance(stage, dict):
            raise SkillExecutionError("mechanism.gear_train stage must be an object")
        driving = stage.get("driving_teeth")
        driven = stage.get("driven_teeth")
        if not isinstance(driving, int) or not isinstance(driven, int):
            raise SkillExecutionError("mechanism.gear_train teeth counts must be integers")
        if driving <= 0 or driven <= 0:
            raise SkillExecutionError("mechanism.gear_train teeth counts must be positive")
        parsed.append({"driving_teeth": driving, "driven_teeth": driven})
    return parsed


def _stage_step(index: int, stage: dict[str, int], stage_ratio: Fraction) -> Step:
    driving_label = 2 * index - 1
    driven_label = 2 * index
    return Step(
        index=index,
        description=(
            f"第 {index} 级：主动轮 z{driving_label}={stage['driving_teeth']}，"
            f"从动轮 z{driven_label}={stage['driven_teeth']}"
        ),
        formula_latex=(
            rf"i_{index}=\frac{{z_{driven_label}}}{{z_{driving_label}}}"
            rf"=\frac{{{stage['driven_teeth']}}}{{{stage['driving_teeth']}}}"
            rf"={_format_number(stage_ratio)}"
        ),
    )


def _context_text(question: NormalizedQuestion) -> str:
    return (
        f"题目：{question.normalized_text}\n"
        f"OCR文字：{question.ocr_text or '无'}\n"
        f"图像描述：{question.vision_description or '无'}"
    )


def _prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


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


def _fraction_latex(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return rf"\frac{{{value.numerator}}}{{{value.denominator}}}"


def _format_number(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    as_float = value.numerator / value.denominator
    return f"{as_float:.6g}"


def _explanation(ratio: Fraction, stages_count: int) -> StudentExplanation:
    return StudentExplanation(
        summary=f"该齿轮系共 {stages_count} 级，总传动比 i={_format_number(ratio)}。",
        intuition="齿轮传动比由每一级的从动轮齿数除以主动轮齿数决定，多级传动再连乘。",
        step_by_step=[
            "先按动力传递顺序划分每一级啮合。",
            "每一级计算 i_k = 从动轮齿数 / 主动轮齿数。",
            "把所有级的传动比相乘得到总传动比。",
        ],
        common_mistake="常见错误是把齿数比写反，或漏乘中间某一级。",
        self_check_question="如果第一级主动轮和从动轮互换，总传动比会怎样变化？",
    )
