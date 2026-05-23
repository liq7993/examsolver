"""Skill interface and shared skill exceptions."""

from __future__ import annotations

from typing import Protocol

from examsolver.contracts import NormalizedQuestion, SolveResult


class ExamsolverError(Exception):
    """Base class for project-specific recoverable errors."""

    def __init__(self, message: str, *, request_id: str | None = None) -> None:
        super().__init__(message)
        self.request_id = request_id


class ContractError(ExamsolverError):
    """Raised when a contract invariant is broken."""


class NormalizationError(ExamsolverError):
    """Raised when raw input cannot be normalized."""


class ClassificationError(ExamsolverError):
    """Raised when classification fails unexpectedly."""


class DispatchError(ExamsolverError):
    """Raised when dispatch cannot complete."""


class NoSkillFoundError(DispatchError):
    """Raised when no skill can handle a classified question."""


class SkillExecutionError(ExamsolverError):
    """Raised when a skill fails while solving."""


class PersistenceError(ExamsolverError):
    """Raised by future persistence adapters; must not block solve response."""


class Skill(Protocol):
    """Protocol implemented by every detachable skill."""

    name: str
    version: str
    subject: str
    question_types: list[str]

    def can_handle(self, question: NormalizedQuestion) -> bool:
        """Return whether this skill can solve the normalized question."""

    def solve(self, question: NormalizedQuestion) -> SolveResult:
        """Solve the normalized question deterministically."""
