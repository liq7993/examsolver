"""SQLite connection and schema setup."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from examsolver.config import database_path
from examsolver.skills.base import PersistenceError

SCHEMA = """
CREATE TABLE IF NOT EXISTS solve_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    solve_id TEXT NOT NULL UNIQUE,
    request_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    question TEXT NOT NULL,
    question_snippet TEXT NOT NULL,
    subject TEXT,
    question_type TEXT NOT NULL,
    skill TEXT NOT NULL,
    success INTEGER NOT NULL,
    normalized_json TEXT NOT NULL,
    response_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_solve_history_created_at
ON solve_history(created_at DESC);

CREATE TABLE IF NOT EXISTS mistakes (
    id TEXT PRIMARY KEY,
    solve_id TEXT NOT NULL,
    subject TEXT NOT NULL,
    question_type TEXT NOT NULL,
    user_note TEXT,
    review_count INTEGER DEFAULT 0,
    last_review DATETIME,
    created_at DATETIME NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_mistakes_subject
ON mistakes(subject);

CREATE INDEX IF NOT EXISTS idx_mistakes_created_at
ON mistakes(created_at DESC);
"""


def connect(path: Path | None = None) -> sqlite3.Connection:
    """Open a SQLite connection and ensure the schema exists."""

    db_path = path or database_path()
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(db_path)
        connection.row_factory = sqlite3.Row
        connection.executescript(SCHEMA)
        return connection
    except sqlite3.Error as exc:
        raise PersistenceError("failed to open sqlite database") from exc
    except OSError as exc:
        raise PersistenceError("failed to prepare sqlite database path") from exc
