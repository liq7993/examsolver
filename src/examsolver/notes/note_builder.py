"""Build notebook entries from the central solve contract."""

from __future__ import annotations

from examsolver.contracts import NormalizedQuestion, NoteEntry, SolveResult


def build_note(solve_result: SolveResult, normalized: NormalizedQuestion) -> NoteEntry:
    """Build the M1 minimum note shell from a solve result."""

    return NoteEntry(
        solve_id=str(normalized.hints["solve_id"]),
        title=_note_title(normalized.normalized_text),
        question_latex=normalized.normalized_text,
        steps=solve_result.steps,
        answer=solve_result.answer,
        student_explanation=solve_result.student_explanation,
        common_mistakes=_common_mistakes(solve_result),
        related_formulas=[],
        flashcards=[],
        citations=solve_result.citations,
        subject=normalized.subject,
        question_type=solve_result.question_type,
    )


def _note_title(text: str) -> str:
    compact = " ".join(text.split())
    return compact[:32] or "未命名题目"


def _common_mistakes(solve_result: SolveResult) -> list[str]:
    mistakes = solve_result.meta.get("common_mistakes", [])
    if not isinstance(mistakes, list):
        return []
    return [mistake for mistake in mistakes if isinstance(mistake, str)]
