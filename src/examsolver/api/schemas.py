"""Pydantic schemas for the HTTP shell only."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from examsolver.contracts import SolveRequest, SolveResponse, StudentExplanation
from examsolver.storage.history_repo import HistoryItem, HistoryPage


class SolveRequestBody(BaseModel):
    """HTTP request body for POST /solve."""

    question: str = Field(..., min_length=1)
    subject: str | None = None
    context: dict[str, Any] | None = None

    def to_contract(self) -> SolveRequest:
        return SolveRequest(question=self.question, subject=self.subject, context=self.context)


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
        )


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
    max_tokens: int
    temperature: float
