from examsolver.contracts import Citation, NormalizedQuestion, SolveResult, Step
from examsolver.notes.note_builder import build_note


def test_build_note_truncates_title_to_32_chars() -> None:
    note = build_note(_solve_result(), _normalized("abcdefghijklmnopqrstuvwxyz1234567890"))

    assert note.title == "abcdefghijklmnopqrstuvwxyz123456"
    assert len(note.title) == 32


def test_build_note_passes_citations_through() -> None:
    citation = Citation(source="book.pdf", chunk_id="chunk-1", page=3, snippet="snippet")
    note = build_note(_solve_result(citations=[citation]), _normalized("求导"))

    assert note.citations == [citation]


def test_build_note_has_empty_common_mistakes_without_explanation() -> None:
    note = build_note(_solve_result(), _normalized("求导"))

    assert note.student_explanation is None
    assert note.common_mistakes == []
    assert note.related_formulas == []
    assert note.flashcards == []


def _normalized(text: str) -> NormalizedQuestion:
    return NormalizedQuestion(
        raw_text=text,
        normalized_text=text,
        subject="calculus",
        hints={"solve_id": "solve-1"},
    )


def _solve_result(citations: list[Citation] | None = None) -> SolveResult:
    return SolveResult(
        question_type="derivative",
        skill="calculus.derivative",
        steps=[Step(index=1, description="识别表达式", formula_latex="x^2")],
        answer="2x",
        citations=citations or [],
        meta={"success": True},
    )
