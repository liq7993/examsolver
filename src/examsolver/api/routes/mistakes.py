from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from examsolver.api.routes._persistence import repo_call
from examsolver.api.schemas import AddMistakeRequestBody, MistakeEntryBody, UpdateMistakeRequestBody
from examsolver.storage import mistakes_repo as repo

router = APIRouter(tags=["mistakes"])

@router.post("/mistakes", response_model=MistakeEntryBody)
def add_mistake(body: AddMistakeRequestBody) -> MistakeEntryBody:
    entry = repo_call(repo.add_mistake_for_solve, body.solve_id, user_note=body.user_note)
    if entry is None:
        raise HTTPException(status_code=404, detail="solve_id not found")
    return MistakeEntryBody.from_repo(entry)


@router.get("/mistakes", response_model=list[MistakeEntryBody])
def get_mistakes(subject: str | None = None) -> list[MistakeEntryBody]:
    return [MistakeEntryBody.from_repo(entry) for entry in repo_call(repo.list_mistakes, subject=subject)]


@router.patch("/mistakes/{mistake_id}", response_model=MistakeEntryBody)
def patch_mistake(mistake_id: str, body: UpdateMistakeRequestBody) -> MistakeEntryBody:
    entry = repo_call(repo.update_user_note, mistake_id, body.user_note)
    if entry is None:
        raise HTTPException(status_code=404, detail="mistake_id not found")
    return MistakeEntryBody.from_repo(entry)


@router.post("/mistakes/{mistake_id}/review", response_model=MistakeEntryBody)
def review_mistake(mistake_id: str) -> MistakeEntryBody:
    entry = repo_call(repo.record_review, mistake_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="mistake_id not found")
    return MistakeEntryBody.from_repo(entry)


@router.delete("/mistakes/{mistake_id}")
def remove_mistake(mistake_id: str) -> dict[str, bool]:
    if not repo_call(repo.delete_mistake, mistake_id):
        raise HTTPException(status_code=404, detail="mistake_id not found")
    return {"deleted": True}


@router.get("/mistakes/export.md", response_class=Response)
def export_mistakes(subject: str | None = None) -> Response:
    body = repo_call(repo.export_mistakes_markdown, subject=subject)
    return Response(content=body, media_type="text/markdown; charset=utf-8")
