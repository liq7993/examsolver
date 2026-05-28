from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from examsolver.rag.embedder import EMBEDDING_DIMENSION
from examsolver.rag.store_sqlite_vec import (
    RAGStoreError,
    init_schema,
    insert_chunk,
    query_nearest,
)
from examsolver.storage.db import connect


def _vec(first: float, second: float = 0.0) -> list[float]:
    values = [0.0] * EMBEDDING_DIMENSION
    values[0] = first
    values[1] = second
    return values


def test_init_schema_adds_rag_tables_without_breaking_history(tmp_path: Path) -> None:
    db_path = tmp_path / "examsolver.db"
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
                "solve-1",
                "request-1",
                "2026-05-28T00:00:00+00:00",
                "求导",
                "求导",
                "calculus",
                "derivative",
                "calculus.derivative",
                1,
                "{}",
                "{}",
            ),
        )

    init_schema(db_path=db_path)

    with connect(db_path) as connection:
        tables = {
            str(row["name"])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table', 'virtual table')"
            )
        }
        history_count = connection.execute("SELECT COUNT(*) AS count FROM solve_history").fetchone()

    assert {"documents", "chunks", "chunk_vec", "solve_history"} <= tables
    assert history_count is not None
    assert history_count["count"] == 1


def test_insert_chunk_and_query_nearest_by_subject(tmp_path: Path) -> None:
    db_path = tmp_path / "examsolver.db"
    init_schema(db_path=db_path)

    insert_chunk(
        document_id="doc-math",
        title="Calculus",
        subject="math",
        source_path="/books/calculus.pdf",
        pages=10,
        chunk_id="chunk-near",
        page=1,
        text="导数定义",
        chunk_index=0,
        embedding=_vec(1.0, 0.0),
        indexed_at="2026-05-28T00:00:00+00:00",
        db_path=db_path,
    )
    insert_chunk(
        document_id="doc-math",
        title="Calculus",
        subject="math",
        source_path="/books/calculus.pdf",
        pages=10,
        chunk_id="chunk-far",
        page=2,
        text="积分定义",
        chunk_index=1,
        embedding=_vec(0.0, 1.0),
        indexed_at="2026-05-28T00:00:00+00:00",
        db_path=db_path,
    )
    insert_chunk(
        document_id="doc-physics",
        title="Mechanics",
        subject="physics",
        source_path="/books/mechanics.pdf",
        pages=7,
        chunk_id="chunk-other-subject",
        page=1,
        text="受力分析",
        chunk_index=0,
        embedding=_vec(1.0, 0.0),
        indexed_at="2026-05-28T00:00:00+00:00",
        db_path=db_path,
    )

    rows = query_nearest(_vec(1.0, 0.0), "math", 2, db_path=db_path)

    assert [row.id for row in rows] == ["chunk-near", "chunk-far"]
    assert rows[0].document_id == "doc-math"
    assert rows[0].title == "Calculus"
    assert rows[0].subject == "math"
    assert rows[0].source_path == "/books/calculus.pdf"
    assert rows[0].page == 1
    assert rows[0].text == "导数定义"
    assert rows[0].chunk_index == 0
    assert rows[0].distance < rows[1].distance


def test_insert_chunk_rejects_wrong_dimension(tmp_path: Path) -> None:
    with pytest.raises(RAGStoreError, match="embedding dimension must be 384"):
        insert_chunk(
            document_id="doc",
            title="Bad",
            subject="math",
            source_path="/bad.pdf",
            pages=None,
            chunk_id="chunk",
            page=None,
            text="bad",
            chunk_index=0,
            embedding=[1.0, 2.0],
            db_path=tmp_path / "examsolver.db",
        )


def test_sqlite_version_is_checked(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(sqlite3, "sqlite_version", "3.40.1")

    with pytest.raises(RAGStoreError, match="sqlite >= 3.41.0 is required"):
        init_schema(db_path=tmp_path / "examsolver.db")
