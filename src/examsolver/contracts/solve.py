"""Solve contract layer.

This module is the center contract shared by skills, pipeline, services, and
future shells. It must stay free of I/O, web, storage, and concrete skill code.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, Protocol


@dataclass(frozen=True, slots=True)
class Step:
    """Structured solving step for future notebook and RAG surfaces."""

    index: int
    description: str
    formula_latex: str | None = None
    image_hint: str | None = None


@dataclass(frozen=True, slots=True)
class Citation:
    """Source citation returned by RAG-backed skills."""

    source: str
    chunk_id: str
    page: int | None = None
    snippet: str = ""


@dataclass(frozen=True, slots=True)
class FormulaCard:
    """Formula card surfaced on a generated note."""

    title: str
    formula_latex: str
    explanation: str = ""


@dataclass(frozen=True, slots=True)
class Flashcard:
    """Review card generated from a solved question."""

    front: str
    back: str
    card_type: Literal["formula", "concept", "trap"] = "concept"

    @property
    def tag(self) -> str:
        """Backward-compatible alias for older frontend code."""

        return self.card_type


@dataclass(frozen=True, slots=True)
class SolveRequest:
    """Raw input accepted from CLI, tests, or a future HTTP shell."""

    question: str
    subject: str | None = None
    context: dict[str, Any] | None = None
    image_paths: list[str] = field(default_factory=list)
    subject_hint: str | None = None


@dataclass(frozen=True, slots=True)
class NormalizedQuestion:
    """Question shape after input normalization."""

    raw_text: str
    normalized_text: str
    subject: str
    has_image: bool = False
    image_paths: list[str] = field(default_factory=list)
    ocr_text: str = ""
    vision_description: str = ""
    hints: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class StudentExplanation:
    """Student-facing teaching narrative produced by a skill."""

    summary: str
    intuition: str
    step_by_step: list[str]
    common_mistake: str
    self_check_question: str


@dataclass(frozen=True, slots=True)
class PlotSeries:
    """One labelled curve sampled as (x, y) points for deterministic plotting."""

    label: str
    points: tuple[tuple[float, float], ...] = ()


@dataclass(frozen=True, slots=True)
class PlotData:
    """Deterministic function plot derived from a solved result (no LLM)."""

    title: str
    x_label: str
    y_label: str
    series: tuple[PlotSeries, ...] = ()


@dataclass(frozen=True, slots=True)
class SolveResult:
    """Structured result returned by a skill before response formatting."""

    question_type: str
    skill: str
    steps: Sequence[Step]
    answer: str | dict[str, Any] | None
    student_explanation: StudentExplanation | None = None
    meta: dict[str, Any] = field(default_factory=dict)
    skill_version: str = ""
    citations: list[Citation] = field(default_factory=list)
    plot: PlotData | None = None


@dataclass(frozen=True, slots=True)
class NoteEntry:
    """One-question note structure built after solving."""

    solve_id: str
    title: str
    question_latex: str
    steps: Sequence[Step]
    answer: str | dict[str, Any] | None
    student_explanation: StudentExplanation | None
    common_mistakes: list[str]
    related_formulas: list[FormulaCard]
    flashcards: list[Flashcard]
    citations: list[Citation]
    subject: str | None
    question_type: str
    created_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class SolveResponse:
    """Stable outward response shape for a single solved question."""

    success: bool
    solve_id: str
    subject: str | None
    question_type: str
    skill: str
    steps: list[str]
    answer: str | dict[str, Any] | None
    message: str
    student_explanation: StudentExplanation | None = None
    citations: list[Citation] = field(default_factory=list)
    fallback_reasons: list[str] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)
    note: NoteEntry | None = None
    plot: PlotData | None = None


class ExplanationEnhancer(Protocol):
    """Optional teaching-layer enhancer for LLM-backed explanations."""

    name: str
    version: str

    def enhance(
        self,
        question: NormalizedQuestion,
        result: SolveResult,
    ) -> StudentExplanation | None:
        """Return an optional student explanation without changing solve facts."""
