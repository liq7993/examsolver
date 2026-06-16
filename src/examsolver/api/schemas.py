"""Pydantic schemas for the HTTP shell only."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from examsolver.contracts import (
    Citation,
    Flashcard,
    FormulaCard,
    NoteEntry,
    SolveRequest,
    SolveResponse,
    Step,
    StudentExplanation,
)
from examsolver.storage.history_repo import HistoryItem, HistoryPage
from examsolver.storage.mistakes_repo import MistakeEntry


class SolveRequestBody(BaseModel):
    """HTTP request body for POST /solve."""

    question: str = Field(..., min_length=1)
    subject: str | None = None
    context: dict[str, Any] | None = None
    image_paths: list[str] = Field(default_factory=list)

    def to_contract(self) -> SolveRequest:
        return SolveRequest(
            question=self.question,
            subject=self.subject,
            context=self.context,
            image_paths=self.image_paths,
        )


class StudentExplanationBody(BaseModel):
    """HTTP response shape for student-facing explanation."""

    summary: str
    intuition: str
    step_by_step: list[str]
    common_mistake: str
    self_check_question: str

    @classmethod
    def from_contract(cls, explanation: StudentExplanation) -> StudentExplanationBody:
        return cls(
            summary=explanation.summary,
            intuition=explanation.intuition,
            step_by_step=explanation.step_by_step,
            common_mistake=explanation.common_mistake,
            self_check_question=explanation.self_check_question,
        )


class StepBody(BaseModel):
    index: int
    description: str
    formula_latex: str | None
    image_hint: str | None

    @classmethod
    def from_contract(cls, step: Step) -> StepBody:
        return cls(
            index=step.index,
            description=step.description,
            formula_latex=step.formula_latex,
            image_hint=step.image_hint,
        )


class CitationBody(BaseModel):
    source: str
    chunk_id: str
    page: int | None
    snippet: str

    @classmethod
    def from_contract(cls, citation: Citation) -> CitationBody:
        return cls(
            source=citation.source,
            chunk_id=citation.chunk_id,
            page=citation.page,
            snippet=citation.snippet,
        )


class FormulaCardBody(BaseModel):
    title: str
    formula_latex: str
    explanation: str

    @classmethod
    def from_contract(cls, card: FormulaCard) -> FormulaCardBody:
        return cls(
            title=card.title,
            formula_latex=card.formula_latex,
            explanation=card.explanation,
        )


class FlashcardBody(BaseModel):
    front: str
    back: str
    card_type: str

    @classmethod
    def from_contract(cls, card: Flashcard) -> FlashcardBody:
        return cls(front=card.front, back=card.back, card_type=card.card_type)


class NoteEntryBody(BaseModel):
    solve_id: str
    title: str
    question_latex: str
    steps: list[StepBody]
    answer: str | dict[str, Any] | None
    student_explanation: StudentExplanationBody | None
    common_mistakes: list[str]
    related_formulas: list[FormulaCardBody]
    flashcards: list[FlashcardBody]
    citations: list[CitationBody]
    subject: str | None
    question_type: str
    created_at: str | None

    @classmethod
    def from_contract(cls, note: NoteEntry) -> NoteEntryBody:
        return cls(
            solve_id=note.solve_id,
            title=note.title,
            question_latex=note.question_latex,
            steps=[StepBody.from_contract(step) for step in note.steps],
            answer=note.answer,
            student_explanation=(
                StudentExplanationBody.from_contract(note.student_explanation)
                if note.student_explanation is not None
                else None
            ),
            common_mistakes=note.common_mistakes,
            related_formulas=[
                FormulaCardBody.from_contract(card) for card in note.related_formulas
            ],
            flashcards=[FlashcardBody.from_contract(card) for card in note.flashcards],
            citations=[CitationBody.from_contract(citation) for citation in note.citations],
            subject=note.subject,
            question_type=note.question_type,
            created_at=note.created_at.isoformat() if note.created_at is not None else None,
        )


class SolveResponseBody(BaseModel):
    """HTTP response body for solve responses."""

    success: bool
    solve_id: str
    subject: str | None
    question_type: str
    skill: str
    steps: list[str]
    answer: str | dict[str, Any] | None
    message: str
    student_explanation: StudentExplanationBody | None = None
    citations: list[CitationBody]
    fallback_reasons: list[str]
    diagnostics: dict[str, Any]
    note: NoteEntryBody | None

    @classmethod
    def from_contract(cls, response: SolveResponse) -> SolveResponseBody:
        explanation = response.student_explanation
        return cls(
            success=response.success,
            solve_id=response.solve_id,
            subject=response.subject,
            question_type=response.question_type,
            skill=response.skill,
            steps=response.steps,
            answer=response.answer,
            message=response.message,
            student_explanation=(
                StudentExplanationBody.from_contract(explanation)
                if explanation is not None
                else None
            ),
            citations=[CitationBody.from_contract(citation) for citation in response.citations],
            fallback_reasons=response.fallback_reasons,
            diagnostics=response.diagnostics,
            note=NoteEntryBody.from_contract(response.note) if response.note is not None else None,
        )


class UploadedImageBody(BaseModel):
    image_path: str


class HistoryItemBody(BaseModel):
    """Flat history item for sidebar rendering."""

    solve_id: str
    subject: str | None
    question_type: str
    skill: str
    success: bool
    created_at: str
    question_snippet: str

    @classmethod
    def from_repo(cls, item: HistoryItem) -> HistoryItemBody:
        return cls(
            solve_id=item.solve_id,
            subject=item.subject,
            question_type=item.question_type,
            skill=item.skill,
            success=item.success,
            created_at=item.created_at,
            question_snippet=item.question_snippet,
        )


class HistoryPageBody(BaseModel):
    """Paginated history response."""

    items: list[HistoryItemBody]
    limit: int
    offset: int
    has_more: bool
    next_offset: int | None

    @classmethod
    def from_repo(cls, page: HistoryPage) -> HistoryPageBody:
        return cls(
            items=[HistoryItemBody.from_repo(item) for item in page.items],
            limit=page.limit,
            offset=page.offset,
            has_more=page.has_more,
            next_offset=page.next_offset,
        )


class SubjectCapabilityBody(BaseModel):
    """Supported question types grouped by subject."""

    name: str
    question_types: list[str]


class SkillCapabilityBody(BaseModel):
    """Registered skill capability entry."""

    name: str
    version: str
    subject: str
    question_types: list[str]


class CapabilitiesBody(BaseModel):
    """Capabilities response for sidebar and client feature discovery."""

    subjects: list[SubjectCapabilityBody]
    skills: list[SkillCapabilityBody]


class LLMStatusBody(BaseModel):
    """Optional local LLM runtime status."""

    provider: str
    enabled: bool
    base_url: str
    model: str
    model_path: str | None
    model_path_exists: bool
    server_reachable: bool
    server_model_count: int | None
    server_error: str | None
    timeout_seconds: float
    temperature: float
    max_tokens: int


class AddMistakeRequestBody(BaseModel):
    solve_id: str = Field(..., min_length=1)
    user_note: str | None = None


class UpdateMistakeRequestBody(BaseModel):
    user_note: str | None = None


class MistakeEntryBody(BaseModel):
    id: str
    solve_id: str
    subject: str
    question_type: str
    user_note: str | None
    review_count: int
    last_review: str | None
    created_at: str

    @classmethod
    def from_repo(cls, entry: MistakeEntry) -> MistakeEntryBody:
        return cls(
            id=entry.id,
            solve_id=entry.solve_id,
            subject=entry.subject,
            question_type=entry.question_type,
            user_note=entry.user_note,
            review_count=entry.review_count,
            last_review=entry.last_review,
            created_at=entry.created_at,
        )
