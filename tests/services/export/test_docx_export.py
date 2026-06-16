from io import BytesIO
from zipfile import ZipFile

from docx import Document

from examsolver.contracts import NoteEntry, Step
from examsolver.services.export.docx_export import export_note_to_docx


def test_export_note_to_docx_is_readable_and_contains_native_math() -> None:
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

    payload = export_note_to_docx(note)

    reopened = Document(BytesIO(payload))
    assert "导数题" in "\n".join(paragraph.text for paragraph in reopened.paragraphs)
    with ZipFile(BytesIO(payload)) as archive:
        document_xml = archive.read("word/document.xml").decode("utf-8")
    assert "<m:oMath>" in document_xml
    assert "<m:f>" in document_xml
