"""Tolerance fit-type hybrid skill."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, cast

from examsolver.contracts import Citation, NormalizedQuestion, SolveResult, Step, StudentExplanation
from examsolver.llm.base import LLMClient, Message
from examsolver.rag.retriever import TextbookChunk, retrieve
from examsolver.skills.base import SkillExecutionError
from examsolver.skills.tolerance._tables import (
    BasicDeviation,
    judge_fit_type,
    lookup_basic_deviation,
)

EXTRACT_SCHEMA: dict[str, object] = {
    "type": "object",
    "required": ["hole_symbol", "shaft_symbol"],
    "properties": {
        "hole_symbol": {"type": "string"},
        "shaft_symbol": {"type": "string"},
    },
    "additionalProperties": False,
}
_PROMPT_PATH = Path(__file__).with_name("prompts") / "fit_type_extract.zh.md"
_GRADED_SYMBOL_PATTERN = re.compile(r"\b([A-Za-z])\s*(\d{1,2})\b")
_BARE_HOLE_SHAFT_PATTERN = re.compile(r"\b([HhGgKk])\b")
RagRetrieve = Callable[[str, str, int], list[TextbookChunk]]


class FitTypeSkill:
    """Hybrid RAG + extraction + table lookup skill for fits."""

    name = "tolerance.fit_type"
    version = "0.1.0"
    subject = "tolerance"
    question_types = ["fit_type"]
    skill_type = "hybrid"
    needs_vision = False
    needs_rag = True

    def can_handle(self, question: NormalizedQuestion) -> bool:
        text = question.normalized_text.lower()
        return any(
            keyword in text
            for keyword in ("配合", "公差", "基本偏差", "h7", "g6", "fit", "tolerance")
        )

    def solve(
        self,
        question: NormalizedQuestion,
        *,
        llm: LLMClient | None = None,
        rag_retrieve: RagRetrieve | None = None,
        rag_chunks: Sequence[TextbookChunk] | None = None,
    ) -> SolveResult:
        chunks = (
            list(rag_chunks)
            if rag_chunks is not None
            else _retrieve_chunks(question, rag_retrieve=rag_retrieve)
        )
        params = _extract_symbols(question, chunks=chunks, llm=llm)
        try:
            hole = lookup_basic_deviation(params["hole_symbol"], "hole")
            shaft = lookup_basic_deviation(params["shaft_symbol"], "shaft")
        except ValueError as exc:
            raise SkillExecutionError("tolerance.fit_type table lookup failed") from exc

        fit_type = judge_fit_type(hole, shaft)
        min_clearance = hole.lower_um - shaft.upper_um
        max_clearance = hole.upper_um - shaft.lower_um
        citations = [_citation_from_chunk(chunk) for chunk in chunks]

        return SolveResult(
            question_type="fit_type",
            skill=self.name,
            skill_version=self.version,
            steps=[
                Step(index=1, description=f"识别孔公差带代号 {params['hole_symbol']}"),
                Step(index=2, description=f"识别轴公差带代号 {params['shaft_symbol']}"),
                Step(
                    index=3,
                    description=(
                        f"查 ISO 286 简表：孔 {hole.lower_um}~{hole.upper_um} μm，"
                        f"轴 {shaft.lower_um}~{shaft.upper_um} μm"
                    ),
                ),
                Step(
                    index=4,
                    description=(
                        f"计算间隙范围 {min_clearance}~{max_clearance} μm，"
                        f"判定为{fit_type}配合"
                    ),
                ),
            ],
            answer=f"{params['hole_symbol']}/{params['shaft_symbol']} 属于{fit_type}配合",
            student_explanation=_explanation(params["hole_symbol"], params["shaft_symbol"], fit_type),
            citations=citations,
            meta={
                "success": True,
                "skill_version": self.version,
                "message": "已完成配合类型判定。",
                "tolerance.fit_type.hole_symbol": params["hole_symbol"],
                "tolerance.fit_type.shaft_symbol": params["shaft_symbol"],
                "tolerance.fit_type.hole": _deviation_meta(hole),
                "tolerance.fit_type.shaft": _deviation_meta(shaft),
                "tolerance.fit_type.min_clearance_um": min_clearance,
                "tolerance.fit_type.max_clearance_um": max_clearance,
                "tolerance.fit_type.fit_type": fit_type,
                "tolerance.fit_type.citation_count": len(citations),
                "common_mistakes": [
                    "不要把大写 H 和小写 h 混为同一个零件；大写通常表示孔，小写通常表示轴。",
                    "判断配合类型要比较孔、轴两个公差带的上下偏差，不能只看字母。",
                ],
            },
        )


def _retrieve_chunks(
    question: NormalizedQuestion,
    *,
    rag_retrieve: RagRetrieve | None,
) -> list[TextbookChunk]:
    retriever = rag_retrieve or retrieve
    try:
        return retriever(question.normalized_text, "tolerance", 3)
    except Exception:
        return []


def _extract_symbols(
    question: NormalizedQuestion,
    *,
    chunks: list[TextbookChunk],
    llm: LLMClient | None,
) -> dict[str, str]:
    if llm is not None:
        try:
            payload = _extract_with_llm(question, chunks=chunks, llm=llm)
            return _validate_params(payload)
        except Exception as exc:
            raise SkillExecutionError("tolerance.fit_type LLM extraction failed") from exc
    return _extract_with_regex(question.normalized_text)


def _extract_with_llm(
    question: NormalizedQuestion,
    *,
    chunks: list[TextbookChunk],
    llm: LLMClient,
) -> dict[str, Any]:
    textbook_context = "\n---\n".join(chunk.text for chunk in chunks) if chunks else "（无教材命中）"
    raw = llm.chat(
        [
            Message(role="system", content=_prompt()),
            Message(
                role="user",
                content=f"题目：{question.normalized_text}\n教材片段：{textbook_context}",
            ),
        ],
        json_schema=EXTRACT_SCHEMA,
        max_tokens=256,
        temperature=0.0,
    )
    data = json.loads(_strip_code_fence(raw))
    if not isinstance(data, dict):
        raise ValueError("fit_type extraction must be a JSON object")
    return cast(dict[str, Any], data)


def _extract_with_regex(text: str) -> dict[str, str]:
    normalized = text.replace("／", "/")
    symbols = [f"{letter}{grade}" for letter, grade in _GRADED_SYMBOL_PATTERN.findall(normalized)]
    if not symbols:
        symbols = _BARE_HOLE_SHAFT_PATTERN.findall(normalized)
    hole = next((symbol for symbol in symbols if symbol[0].isupper()), None)
    shaft = next((symbol for symbol in symbols if symbol[0].islower()), None)
    if hole is None or shaft is None:
        raise SkillExecutionError("tolerance.fit_type could not extract hole/shaft symbols")
    return {"hole_symbol": hole, "shaft_symbol": shaft}


def _validate_params(payload: dict[str, Any]) -> dict[str, str]:
    hole_symbol = payload.get("hole_symbol")
    shaft_symbol = payload.get("shaft_symbol")
    if not isinstance(hole_symbol, str) or not hole_symbol.strip():
        raise ValueError("hole_symbol must be a non-empty string")
    if not isinstance(shaft_symbol, str) or not shaft_symbol.strip():
        raise ValueError("shaft_symbol must be a non-empty string")
    return {"hole_symbol": hole_symbol.strip(), "shaft_symbol": shaft_symbol.strip()}


def _citation_from_chunk(chunk: TextbookChunk) -> Citation:
    return Citation(
        source=chunk.document_title,
        chunk_id=chunk.id,
        page=chunk.page,
        snippet=chunk.text[:200],
    )


def _deviation_meta(deviation: BasicDeviation) -> dict[str, int | str]:
    return {
        "symbol": deviation.symbol,
        "component": deviation.component,
        "letter": deviation.letter,
        "grade": deviation.grade,
        "lower_um": deviation.lower_um,
        "upper_um": deviation.upper_um,
    }


def _explanation(hole_symbol: str, shaft_symbol: str, fit_type: str) -> StudentExplanation:
    return StudentExplanation(
        summary=f"{hole_symbol}/{shaft_symbol} 判定为{fit_type}配合。",
        intuition="配合类型取决于孔公差带和轴公差带相对位置，而不是只看一个代号。",
        step_by_step=[
            f"先把大写 {hole_symbol} 作为孔公差带。",
            f"再把小写 {shaft_symbol} 作为轴公差带。",
            "查表得到两个公差带的上下偏差后比较间隙范围。",
            f"根据间隙范围符号判定为{fit_type}配合。",
        ],
        common_mistake="常见错误是只背 H 或 g 的含义，却没有比较孔和轴两个区间。",
        self_check_question="如果把轴从 g6 换成 k6，最小间隙的符号会不会改变？",
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
