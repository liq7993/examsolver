"""Solve routes for the HTTP shell."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Query, UploadFile

from examsolver.api.schemas import (
    HistoryPageBody,
    SolveRequestBody,
    SolveResponseBody,
    UploadedImageBody,
)
from examsolver.services.solve_service import generate_flashcards_for_solve, solve
from examsolver.storage.history_repo import get_response, list_history
from examsolver.storage.uploads import InvalidImageUpload, store_image_upload

router = APIRouter(tags=["solve"])


@router.post("/solve/images", response_model=UploadedImageBody)
async def upload_solve_image(file: UploadFile = File(...)) -> UploadedImageBody:
    """Store a browser-uploaded image for the OCR/vision solve pipeline."""

    try:
        path = store_image_upload(
            content=await file.read(),
            content_type=file.content_type,
        )
    except InvalidImageUpload as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return UploadedImageBody(image_path=str(path))


@router.post("/solve", response_model=SolveResponseBody)
def solve_question(
    body: SolveRequestBody,
    background_tasks: BackgroundTasks,
) -> SolveResponseBody:
    """Solve synchronously, then kick flashcard generation to the background.

    The deterministic answer plus the local explanation return immediately; the
    slow flashcard cloud call runs after the response via a background task, so
    /solve stays fast and the cards land on the note in time for the next view.
    """

    response = solve(body.to_contract())
    background_tasks.add_task(generate_flashcards_for_solve, response.solve_id)
    return SolveResponseBody.from_contract(response)


@router.get("/solve/history", response_model=HistoryPageBody)
def solve_history(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> HistoryPageBody:
    """Return newest-first solve history summaries."""

    return HistoryPageBody.from_repo(list_history(limit=limit, offset=offset))


@router.get("/solve/{solve_id}", response_model=SolveResponseBody)
def get_solve(solve_id: str) -> SolveResponseBody:
    """Return one stored solve response by solve_id (never blocks on flashcards)."""

    response = get_response(solve_id)
    if response is None:
        raise HTTPException(status_code=404, detail="solve_id not found")
    return SolveResponseBody.from_contract(response)
