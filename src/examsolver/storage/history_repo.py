"""Repository for solve history persistence and lookup."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from examsolver.contracts import Citation, NormalizedQuestion, SolveResponse, StudentExplanation
from examsolver.skills.base import PersistenceError
from examsolver.storage.db import connect

DEFAULT_LIMIT = 50
MAX_LIMIT = 100


@dataclass(frozen=True, slots=True)
class HistoryItem:
    """Flat history row for sidebar/list rendering."""

    solve_id: str
    subject: str | None
    question_type: str
    skill: str
    success: bool
    created_at: str
    question_snippet: str


@dataclass(frozen=True, slots=True)
class HistoryPage:
    """Paginated solve history list."""

    items: list[HistoryItem]
    limit: int
    offset: int
    has_more: bool
    next_offset: int | None


@dataclass(frozen=True, slots=True)
class SolveSnapshot:
    """Complete stored solve snapshot for export surfaces."""

    question: str
    response: SolveResponse


def save_history(
    *,
    question: NormalizedQuestion,
    response: SolveResponse,
    db_path: Path | None = None,
) -> None:
    """Persist a complete solve snapshot."""

    request_id = str(question.hints.get("request_id", "unknown"))
    created_at = str(question.hints.get("created_at", ""))
    try:
        with connect(db_path) as connection:
            connection.execute(
                """
                INSERT INTO solve_history (
                    solve_id, request_id, created_at, question, question_snippet,
                    subject, question_type, skill, success, normalized_json, response_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    response.solve_id,
                    request_id,
                    created_at,
                    question.raw_text,
                    _snippet(question.raw_text),
                    response.subject,
                    response.question_type,
                    response.skill,
                    int(response.success),
                    json.dumps(asdict(question), ensure_ascii=False),
                    json.dumps(asdict(response), ensure_ascii=False),
                ),
            )
    except (sqlite3.Error, OSError) as exc:
        raise PersistenceError("failed to save solve history", request_id=request_id) from exc


def list_history(
    *,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    db_path: Path | None = None,
) -> HistoryPage:
    """Return a flat, newest-first history page."""

    safe_limit = _clamp_limit(limit)
    safe_offset = max(offset, 0)
    try:
        with connect(db_path) as connection:
            rows = connection.execute(
                """
                SELECT solve_id, subject, question_type, skill, success, created_at, question_snippet
                FROM solve_history
                ORDER BY created_at DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                (safe_limit + 1, safe_offset),
            ).fetchall()
    except (sqlite3.Error, OSError) as exc:
        raise PersistenceError("failed to list solve history") from exc

    visible_rows = rows[:safe_limit]
    has_more = len(rows) > safe_limit
    return HistoryPage(
        items=[
            HistoryItem(
                solve_id=str(row["solve_id"]),
                subject=row["subject"],
                question_type=str(row["question_type"]),
                skill=str(row["skill"]),
                success=bool(row["success"]),
                created_at=str(row["created_at"]),
                question_snippet=str(row["question_snippet"]),
            )
            for row in visible_rows
        ],
        limit=safe_limit,
        offset=safe_offset,
        has_more=has_more,
        next_offset=safe_offset + safe_limit if has_more else None,
    )


def get_response(solve_id: str, *, db_path: Path | None = None) -> SolveResponse | None:
    """Return a stored SolveResponse by solve_id."""

    snapshot = get_snapshot(solve_id, db_path=db_path)
    return snapshot.response if snapshot is not None else None


def get_snapshot(solve_id: str, *, db_path: Path | None = None) -> SolveSnapshot | None:
    """Return the stored question and SolveResponse by solve_id."""

    try:
        with connect(db_path) as connection:
            row = connection.execute(
                "SELECT question, response_json FROM solve_history WHERE solve_id = ?",
                (solve_id,),
            ).fetchone()
    except (sqlite3.Error, OSError) as exc:
        raise PersistenceError("failed to fetch solve history") from exc

    if row is None:
        return None
    return SolveSnapshot(
        question=str(row["question"]),
        response=_response_from_json(str(row["response_json"])),
    )


def _response_from_json(payload: str) -> SolveResponse:
    data = json.loads(payload)
    explanation_data = data.get("student_explanation")
    explanation = (
        StudentExplanation(**explanation_data) if isinstance(explanation_data, dict) else None
    )
    return SolveResponse(
        success=bool(data["success"]),
        solve_id=str(data["solve_id"]),
        subject=data.get("subject"),
        question_type=str(data["question_type"]),
        skill=str(data["skill"]),
        steps=[str(step) for step in data["steps"]],
        answer=_answer_from_json(data.get("answer")),
        message=str(data["message"]),
        student_explanation=explanation,
        citations=_citations_from_json(data.get("citations")),
        fallback_reasons=[str(reason) for reason in data.get("fallback_reasons", [])],
        diagnostics=dict(data.get("diagnostics", {})),
    )


def _answer_from_json(value: Any) -> str | dict[str, Any] | None:
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, dict):
        return value
    return str(value)


def _citations_from_json(value: Any) -> list[Citation]:
    if not isinstance(value, list):
        return []
    citations: list[Citation] = []
    for item in value:
        if isinstance(item, dict):
            citations.append(
                Citation(
                    source=str(item.get("source", "")),
                    chunk_id=str(item.get("chunk_id", "")),
                    page=item.get("page") if isinstance(item.get("page"), int) else None,
                    snippet=str(item.get("snippet", "")),
                )
            )
    return citations


def _snippet(question: str) -> str:
    compact = " ".join(question.split())
    return compact[:80]


def _clamp_limit(limit: int) -> int:
    return min(max(limit, 1), MAX_LIMIT)
