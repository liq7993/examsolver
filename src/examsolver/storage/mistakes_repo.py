"""Repository for mistake-book persistence and export."""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from examsolver.skills.base import PersistenceError
from examsolver.storage.db import connect
from examsolver.storage.history_repo import get_response


@dataclass(frozen=True, slots=True)
class MistakeEntry:
    id: str
    solve_id: str
    subject: str
    question_type: str
    user_note: str | None
    review_count: int
    last_review: str | None
    created_at: str


def add_mistake_for_solve(
    solve_id: str,
    *,
    user_note: str | None = None,
    db_path: Path | None = None,
) -> MistakeEntry | None:
    """Create a mistake entry from stored solve metadata."""

    response = get_response(solve_id, db_path=db_path)
    if response is None:
        return None
    return add_mistake(
        solve_id=solve_id,
        subject=response.subject or "unknown",
        question_type=response.question_type,
        user_note=user_note,
        db_path=db_path,
    )


def add_mistake(
    *,
    solve_id: str,
    subject: str,
    question_type: str,
    user_note: str | None = None,
    db_path: Path | None = None,
) -> MistakeEntry:
    """Insert one mistake row and return it."""

    entry = MistakeEntry(
        id=uuid.uuid4().hex,
        solve_id=solve_id,
        subject=subject,
        question_type=question_type,
        user_note=user_note,
        review_count=0,
        last_review=None,
        created_at=datetime.now(UTC).isoformat(),
    )
    try:
        with connect(db_path) as connection:
            connection.execute(
                """
                INSERT INTO mistakes (
                    id, solve_id, subject, question_type, user_note,
                    review_count, last_review, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.id,
                    entry.solve_id,
                    entry.subject,
                    entry.question_type,
                    entry.user_note,
                    entry.review_count,
                    entry.last_review,
                    entry.created_at,
                ),
            )
    except (sqlite3.Error, OSError) as exc:
        raise PersistenceError("failed to add mistake") from exc
    return entry


def list_mistakes(*, subject: str | None = None, db_path: Path | None = None) -> list[MistakeEntry]:
    """Return mistake rows newest first, optionally filtered by subject."""

    where = "WHERE subject = ?" if subject else ""
    params = (subject,) if subject else ()
    try:
        with connect(db_path) as connection:
            rows = connection.execute(
                f"""
                SELECT id, solve_id, subject, question_type, user_note,
                       review_count, last_review, created_at
                FROM mistakes
                {where}
                ORDER BY created_at DESC
                """,
                params,
            ).fetchall()
    except (sqlite3.Error, OSError) as exc:
        raise PersistenceError("failed to list mistakes") from exc
    return [_entry_from_row(row) for row in rows]


def update_user_note(
    mistake_id: str,
    user_note: str | None,
    *,
    db_path: Path | None = None,
) -> MistakeEntry | None:
    """Update one mistake note."""

    try:
        with connect(db_path) as connection:
            cursor = connection.execute(
                "UPDATE mistakes SET user_note = ? WHERE id = ?",
                (user_note, mistake_id),
            )
            if cursor.rowcount == 0:
                return None
            row = connection.execute(
                """
                SELECT id, solve_id, subject, question_type, user_note,
                       review_count, last_review, created_at
                FROM mistakes WHERE id = ?
                """,
                (mistake_id,),
            ).fetchone()
    except (sqlite3.Error, OSError) as exc:
        raise PersistenceError("failed to update mistake") from exc
    return _entry_from_row(row) if row is not None else None


def delete_mistake(mistake_id: str, *, db_path: Path | None = None) -> bool:
    """Delete one mistake row."""

    try:
        with connect(db_path) as connection:
            cursor = connection.execute("DELETE FROM mistakes WHERE id = ?", (mistake_id,))
    except (sqlite3.Error, OSError) as exc:
        raise PersistenceError("failed to delete mistake") from exc
    return cursor.rowcount > 0


def export_mistakes_markdown(*, subject: str | None = None, db_path: Path | None = None) -> str:
    """Export mistake rows as a compact Markdown document."""

    entries = list_mistakes(subject=subject, db_path=db_path)
    title = f"# 错题本（{subject}）" if subject else "# 错题本"
    lines = [title, ""]
    if not entries:
        lines.append("暂无错题。")
        return "\n".join(lines)
    for entry in entries:
        lines.extend(
            [
                f"## {entry.subject} / {entry.question_type}",
                f"- solve_id: `{entry.solve_id}`",
                f"- mistake_id: `{entry.id}`",
                f"- created_at: {entry.created_at}",
                f"- user_note: {entry.user_note or ''}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _entry_from_row(row: sqlite3.Row) -> MistakeEntry:
    return MistakeEntry(
        id=str(row["id"]),
        solve_id=str(row["solve_id"]),
        subject=str(row["subject"]),
        question_type=str(row["question_type"]),
        user_note=row["user_note"] if row["user_note"] is None else str(row["user_note"]),
        review_count=int(row["review_count"]),
        last_review=row["last_review"] if row["last_review"] is None else str(row["last_review"]),
        created_at=str(row["created_at"]),
    )
