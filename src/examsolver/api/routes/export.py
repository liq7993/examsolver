"""Export routes for stored solve artifacts."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from examsolver.services.export.markdown_exporter import export_to_markdown
from examsolver.storage.history_repo import get_snapshot

router = APIRouter(tags=["export"])


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
