"""Question router with deterministic rules and an LLM fallback."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from examsolver.contracts import NormalizedQuestion
from examsolver.llm.base import LLMClient, Message
from examsolver.llm.router import pick_llm
from examsolver.pipeline.classifier import classify
from examsolver.skills.registry import list_skills

REGEX_CONFIDENCE_THRESHOLD = 0.7
LLM_ROUTE_TASK = "route"
KNOWN_SUBJECTS = {
    "general",
    "calculus",
    "physics",
    "mechanics_eng",
    "mechanism",
    "tolerance",
    "auto_theory",
}
KNOWN_QUESTION_TYPES = {
    "unknown",
}
_PROMPT_PATH = Path(__file__).with_name("prompts") / "router_agent.zh.md"


@dataclass(frozen=True, slots=True)
class RouteDecision:
    """Question routing output written into graph state."""

    subject: str
    question_type: str
    confidence: float
    reasoning: str
    fallback_reasons: tuple[str, ...] = ()


def route_question(
    question: NormalizedQuestion,
    *,
    llm_client: LLMClient | None = None,
) -> RouteDecision:
    """Route one normalized question with regex first, then an LLM JSON fallback."""

    question_type = classify(question)
    if question_type != "unknown":
        confidence = 1.0
        if confidence >= REGEX_CONFIDENCE_THRESHOLD:
            return RouteDecision(
                subject=question.subject,
                question_type=question_type,
                confidence=confidence,
                reasoning="regex",
            )

    return _route_with_llm(question, llm_client=llm_client)


def _route_with_llm(
    question: NormalizedQuestion,
    *,
    llm_client: LLMClient | None,
) -> RouteDecision:
    fallback_reasons: list[str] = []
    client = llm_client
    if client is None:
        try:
            client = pick_llm(LLM_ROUTE_TASK, needs_vision=False)
        except Exception as exc:
            return _unknown(f"pick_llm_failed: {exc}", fallback_reasons=("llm_router_failed",))
    if client is None:
        return _unknown("No LLM router is configured.", fallback_reasons=("llm_router_unavailable",))

    try:
        content = client.chat(
            _route_messages(question),
            json_schema=_router_schema(),
            max_tokens=256,
            temperature=0.0,
            timeout=20.0,
        )
        payload = _parse_json_object(content)
        decision = _decision_from_payload(payload)
    except Exception as exc:
        fallback_reasons.append("llm_router_failed")
        return _unknown(f"LLM router failed: {exc}", fallback_reasons=tuple(fallback_reasons))

    if decision is None:
        fallback_reasons.append("llm_router_unknown")
        return _unknown("LLM router returned unknown or unsupported route.", tuple(fallback_reasons))
    return decision


def _route_messages(question: NormalizedQuestion) -> list[Message]:
    prompt = _router_prompt()
    user_payload = {
        "raw_text": question.raw_text,
        "normalized_text": question.normalized_text,
        "subject_hint": question.subject,
        "known_subjects": sorted(KNOWN_SUBJECTS),
        "known_question_types": _known_question_types(),
    }
    return [
        Message(role="system", content=prompt),
        Message(role="user", content=json.dumps(user_payload, ensure_ascii=False)),
    ]


def _router_prompt() -> str:
    try:
        return _PROMPT_PATH.read_text(encoding="utf-8")
    except OSError:
        return (
            "你是 Examsolver 的路由器。只判断题目所属 subject、question_type、"
            "confidence 和 reasoning，并只输出 JSON。"
        )


def _parse_json_object(content: str) -> dict[str, Any]:
    data = json.loads(_strip_code_fence(content))
    if not isinstance(data, dict):
        raise ValueError("router response must be a JSON object")
    return cast(dict[str, Any], data)


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


def _decision_from_payload(payload: dict[str, Any]) -> RouteDecision | None:
    subject = payload.get("subject")
    question_type = payload.get("question_type")
    confidence = payload.get("confidence")
    reasoning = payload.get("reasoning")

    if not isinstance(subject, str) or subject not in KNOWN_SUBJECTS:
        return None
    if not isinstance(question_type, str) or question_type not in set(_known_question_types()):
        return None
    if question_type == "unknown":
        return None
    if not isinstance(confidence, int | float):
        return None
    bounded_confidence = max(0.0, min(1.0, float(confidence)))
    if bounded_confidence <= 0.0:
        return None
    return RouteDecision(
        subject=subject,
        question_type=question_type,
        confidence=bounded_confidence,
        reasoning=reasoning if isinstance(reasoning, str) and reasoning else "llm",
    )


def _unknown(reasoning: str, fallback_reasons: tuple[str, ...]) -> RouteDecision:
    return RouteDecision(
        subject="general",
        question_type="unknown",
        confidence=0.0,
        reasoning=reasoning,
        fallback_reasons=fallback_reasons,
    )


def _known_question_types() -> list[str]:
    question_types = set(KNOWN_QUESTION_TYPES)
    for skill in list_skills():
        raw_types = skill.get("question_types", [])
        if isinstance(raw_types, list):
            question_types.update(item for item in raw_types if isinstance(item, str))
    return sorted(question_types)


def _router_schema() -> dict[str, object]:
    return {
        "type": "object",
        "properties": {
            "subject": {"type": "string", "enum": sorted(KNOWN_SUBJECTS)},
            "question_type": {"type": "string", "enum": _known_question_types()},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "reasoning": {"type": "string"},
        },
        "required": ["subject", "question_type", "confidence", "reasoning"],
        "additionalProperties": False,
    }
