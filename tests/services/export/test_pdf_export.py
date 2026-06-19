from examsolver.contracts import NoteEntry, Step
from examsolver.services.export.pdf_export import export_note_to_pdf


def test_export_note_to_pdf_returns_valid_pdf_bytes() -> None:
    note = NoteEntry(
        solve_id="solve-1",
        title="导数题",
        question_latex="求 x^2 对 x 的导数",
        steps=[Step(index=1, description="使用幂函数法则", formula_latex="x^2")],
        answer="$\\frac{d}{dx}(x^2)=2x$",
        student_explanation=None,
        common_mistakes=["不要漏掉指数。"],
        related_formulas=[],
        flashcards=[],
        citations=[],
        subject="calculus",
        question_type="derivative",
    )

    payload = export_note_to_pdf(note)

    assert payload.startswith(b"%PDF-")
    assert payload.rstrip().endswith(b"%%EOF")
    assert len(payload) > 1000
