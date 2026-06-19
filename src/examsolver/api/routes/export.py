"""Export routes for stored solve artifacts."""

from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from examsolver.services.export.docx_export import export_note_to_docx
from examsolver.services.export.markdown_exporter import export_to_markdown
from examsolver.services.export.pdf_export import export_note_to_pdf
from examsolver.storage.history_repo import get_snapshot

router = APIRouter(tags=["export"])


@router.get("/export/docx/{solve_id}", response_class=Response)
def export_docx(solve_id: str) -> Response:
    """Return a stored one-question note as an editable Word document."""

    snapshot = get_snapshot(solve_id)
    if snapshot is None or snapshot.response.note is None:
        raise HTTPException(status_code=404, detail="solve_id not found")

    note = snapshot.response.note
    created_at = note.created_at or datetime.now(UTC)
    display_filename = f"{note.subject or 'unknown'}-{note.title}-{created_at:%Y-%m-%d}.docx"
    fallback_filename = f"examsolver-{note.subject or 'unknown'}-{created_at:%Y-%m-%d}.docx"
    return Response(
        content=export_note_to_docx(note),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{_safe_filename(fallback_filename)}"; '
                f"filename*=UTF-8''{quote(display_filename)}"
            )
        },
    )


@router.get("/solve/{solve_id}/export.pdf", response_class=Response)
def export_pdf(solve_id: str) -> Response:
    """Return a stored one-question note as a print-quality PDF."""

    snapshot = get_snapshot(solve_id)
    if snapshot is None or snapshot.response.note is None:
        raise HTTPException(status_code=404, detail="solve_id not found")

    note = snapshot.response.note
    created_at = note.created_at or datetime.now(UTC)
    display_filename = f"{note.subject or 'unknown'}-{note.title}-{created_at:%Y-%m-%d}.pdf"
    fallback_filename = f"examsolver-{note.subject or 'unknown'}-{created_at:%Y-%m-%d}.pdf"
    return Response(
        content=export_note_to_pdf(note),
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{_safe_filename(fallback_filename)}"; '
                f"filename*=UTF-8''{quote(display_filename)}"
            )
        },
    )


@router.get("/solve/{solve_id}/export.md", response_class=Response)
def export_markdown(solve_id: str) -> Response:
    """Return a stored solve artifact as Markdown."""

    snapshot = get_snapshot(solve_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="solve_id not found")

    filename = f"examsolver-{snapshot.response.subject or 'unknown'}-{solve_id[:8]}.md"
    return Response(
        content=export_to_markdown(question=snapshot.question, response=snapshot.response),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _safe_filename(value: str) -> str:
    safe = "".join(
        char if char.isascii() and (char.isalnum() or char in {"-", "_", "."}) else "-"
        for char in value
    )
    return safe[:120] or "examsolver-note.docx"
