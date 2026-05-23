"""M1 router agent wrapper around the deterministic classifier."""

from __future__ import annotations

from dataclasses import dataclass

from examsolver.contracts import NormalizedQuestion
from examsolver.pipeline.classifier import classify


@dataclass(frozen=True, slots=True)
class RouteDecision:
    """Question routing output written into graph state."""

    subject: str
    question_type: str
    confidence: float
    reasoning: str


def route_question(question: NormalizedQuestion) -> RouteDecision:
    """Route one normalized question with the M1 deterministic fallback."""

    question_type = classify(question)
    if question_type == "unknown":
        return RouteDecision(
            subject="general",
            question_type="unknown",
            confidence=0.0,
            reasoning="No deterministic classifier rule matched; LLM router is deferred to M2.",
        )

    return RouteDecision(
        subject=question.subject,
        question_type=question_type,
        confidence=1.0,
        reasoning=f"Matched deterministic classifier rule for {question_type}.",
    )
