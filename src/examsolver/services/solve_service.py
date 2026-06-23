"""Solve service orchestration layer."""

from __future__ import annotations

import logging

from examsolver.contracts import ExplanationEnhancer, SolveRequest, SolveResponse
from examsolver.graph import run_solve_graph
from examsolver.llm.router import pick_llm
from examsolver.notes.flashcard import generate_flashcards
from examsolver.storage.history_repo import get_response, update_note_flashcards

logger = logging.getLogger(__name__)


def solve(
    request: SolveRequest,
    *,
    enhancer: ExplanationEnhancer | None = None,
) -> SolveResponse:
    """Run the LangGraph-backed solve orchestration for one question."""

    return run_solve_graph(request, enhancer=enhancer)


def generate_flashcards_for_solve(solve_id: str) -> None:
    """Generate and persist flashcards for a stored solve, off the hot path.

    Flashcards are the only slow part of a solve (a cloud round-trip), so the
    POST /solve handler schedules this as a background task: the response returns
    immediately and the cards land on the note once ready, in time for the next
    view. Best-effort by design -- any failure (no cloud key, parse error,
    network) leaves the note card-less and is logged, never raised, since no
    caller is waiting on it.
    """

    response = get_response(solve_id)
    if response is None or response.note is None or response.note.flashcards:
        return
    try:
        flashcards = generate_flashcards(
            response.note, llm=pick_llm("synthesize", needs_vision=False)
        )
    except Exception as exc:
        logger.warning("background flashcard generation skipped for %s: %s", solve_id, exc)
        return
    if flashcards:
        update_note_flashcards(solve_id, flashcards)
