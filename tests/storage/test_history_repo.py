from dataclasses import replace

from examsolver.contracts import Flashcard, NoteEntry, SolveRequest
from examsolver.pipeline.classifier import classify
from examsolver.pipeline.dispatcher import dispatch_or_unknown
from examsolver.pipeline.formatter import format_response
from examsolver.pipeline.normalizer import normalize
from examsolver.storage.history_repo import (
    get_response,
    get_snapshot,
    list_history,
    save_history,
    update_note_flashcards,
)


def _note(solve_id: str) -> NoteEntry:
    return NoteEntry(
        solve_id=solve_id,
        title="求导",
        question_latex="x^2",
        steps=[],
        answer="2x",
        student_explanation=None,
        common_mistakes=[],
        related_formulas=[],
        flashcards=[],
        citations=[],
        subject="calculus",
        question_type="derivative",
    )


def test_save_list_and_get_history() -> None:
    question = normalize(SolveRequest(question="求 x^2 对 x 的导数"))
    result = dispatch_or_unknown(question, classify(question))
    response = format_response(question, result)

    save_history(question=question, response=response)

    page = list_history(limit=10)
    assert page.has_more is False
    assert page.next_offset is None
    assert len(page.items) == 1
    assert page.items[0].solve_id == response.solve_id
    assert page.items[0].question_snippet == "求 x^2 对 x 的导数"

    stored = get_response(response.solve_id)
    assert stored is not None
    assert stored.solve_id == response.solve_id
    assert stored.answer == "$\\frac{d}{dx}\\left(x^{2}\\right) = 2 x$"

    snapshot = get_snapshot(response.solve_id)
    assert snapshot is not None
    assert snapshot.question == "求 x^2 对 x 的导数"
    assert snapshot.response.solve_id == response.solve_id


def test_history_pagination_reports_next_offset() -> None:
    for index in range(3):
        question = normalize(SolveRequest(question=f"求 x^{index + 2} 对 x 的导数"))
        response = format_response(question, dispatch_or_unknown(question, classify(question)))
        save_history(question=question, response=response)

    page = list_history(limit=2, offset=0)

    assert len(page.items) == 2
    assert page.has_more is True
    assert page.next_offset == 2


def test_update_note_flashcards_round_trips_onto_stored_note() -> None:
    question = normalize(SolveRequest(question="求 x^2 对 x 的导数"))
    result = dispatch_or_unknown(question, classify(question))
    response = replace(format_response(question, result), note=_note("ignored"))
    save_history(question=question, response=response)

    cards = [
        Flashcard(front="前", back="后", card_type="formula"),
        Flashcard(front="概念", back="解释"),
    ]
    assert update_note_flashcards(response.solve_id, cards) is True

    stored = get_response(response.solve_id)
    assert stored is not None
    assert stored.note is not None
    assert [card.front for card in stored.note.flashcards] == ["前", "概念"]
    assert [card.card_type for card in stored.note.flashcards] == ["formula", "concept"]


def test_update_note_flashcards_unknown_solve_id_returns_false() -> None:
    assert update_note_flashcards("missing", [Flashcard(front="a", back="b")]) is False


def test_update_note_flashcards_without_note_returns_false() -> None:
    question = normalize(SolveRequest(question="求 x^2 对 x 的导数"))
    result = dispatch_or_unknown(question, classify(question))
    response = replace(format_response(question, result), note=None)
    save_history(question=question, response=response)

    assert update_note_flashcards(response.solve_id, [Flashcard(front="a", back="b")]) is False
