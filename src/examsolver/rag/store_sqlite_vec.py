"""SQLite-backed RAG vector store using sqlite-vec."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import sqlite_vec  # type: ignore[import-untyped]

from examsolver.rag.embedder import EMBEDDING_DIMENSION
from examsolver.storage.db import connect

MIN_SQLITE_VERSION = (3, 41, 0)

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS documents (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    subject     TEXT NOT NULL,
    source_path TEXT NOT NULL,
    pages       INTEGER,
    indexed_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chunks (
    id          TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(id),
    page        INTEGER,
    text        TEXT NOT NULL,
    chunk_index INTEGER NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS chunk_vec USING vec0(
    chunk_id TEXT PRIMARY KEY,
    embedding FLOAT[{EMBEDDING_DIMENSION}]
);
"""


class RAGStoreError(RuntimeError):
    """Raised when the RAG vector store cannot complete an operation."""


@dataclass(frozen=True, slots=True)
class TextbookChunk:
    """A retrieved textbook chunk with source metadata."""

    id: str
    document_id: str
    title: str
    subject: str
    source_path: str
    page: int | None
    text: str
    chunk_index: int
    distance: float


@dataclass(frozen=True, slots=True)
class IndexedDocument:
    """Stored textbook document metadata."""

    id: str
    title: str
    subject: str
    source_path: str
    pages: int | None
    indexed_at: str


def init_schema(*, db_path: Path | None = None) -> None:
    """Create RAG tables in the existing Examsolver SQLite database."""

    try:
        with _connect_vec(db_path) as connection:
            _ensure_schema(connection)
    except (sqlite3.Error, OSError) as exc:
        raise RAGStoreError("failed to initialize RAG sqlite-vec schema") from exc


def get_document_by_source_path(
    source_path: str,
    *,
    db_path: Path | None = None,
) -> IndexedDocument | None:
    """Return an indexed document by source path, if present."""

    try:
        with _connect_vec(db_path) as connection:
            _ensure_schema(connection)
            row = connection.execute(
                """
                SELECT id, title, subject, source_path, pages, indexed_at
                FROM documents
                WHERE source_path = ?
                """,
                (source_path,),
            ).fetchone()
    except (sqlite3.Error, OSError) as exc:
        raise RAGStoreError("failed to fetch indexed document") from exc
    return None if row is None else _document_from_row(row)


def count_document_chunks(
    document_id: str,
    *,
    db_path: Path | None = None,
) -> int:
    """Return how many chunks are stored for one document."""

    try:
        with _connect_vec(db_path) as connection:
            _ensure_schema(connection)
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM chunks WHERE document_id = ?",
                (document_id,),
            ).fetchone()
    except (sqlite3.Error, OSError) as exc:
        raise RAGStoreError("failed to count document chunks") from exc
    return 0 if row is None else int(row["count"])


def delete_document_by_source_path(
    source_path: str,
    *,
    db_path: Path | None = None,
) -> int:
    """Delete one indexed document and all its chunks/vectors by source path."""

    try:
        with _connect_vec(db_path) as connection:
            _ensure_schema(connection)
            chunk_rows = connection.execute(
                """
                SELECT c.id
                FROM chunks c
                JOIN documents d ON d.id = c.document_id
                WHERE d.source_path = ?
                """,
                (source_path,),
            ).fetchall()
            chunk_ids = [str(row["id"]) for row in chunk_rows]
            for chunk_id in chunk_ids:
                connection.execute("DELETE FROM chunk_vec WHERE chunk_id = ?", (chunk_id,))
            connection.execute(
                """
                DELETE FROM chunks
                WHERE document_id IN (
                    SELECT id FROM documents WHERE source_path = ?
                )
                """,
                (source_path,),
            )
            cursor = connection.execute(
                "DELETE FROM documents WHERE source_path = ?",
                (source_path,),
            )
    except (sqlite3.Error, OSError) as exc:
        raise RAGStoreError("failed to delete indexed document") from exc
    return cursor.rowcount


def insert_chunk(
    *,
    document_id: str,
    title: str,
    subject: str,
    source_path: str,
    pages: int | None,
    chunk_id: str,
    page: int | None,
    text: str,
    chunk_index: int,
    embedding: Sequence[float],
    indexed_at: str | None = None,
    db_path: Path | None = None,
) -> None:
    """Insert or replace one document chunk and its embedding."""

    vector = _serialize_embedding(embedding)
    indexed_at_value = indexed_at or datetime.now(UTC).isoformat()
    try:
        with _connect_vec(db_path) as connection:
            _ensure_schema(connection)
            connection.execute(
                """
                INSERT INTO documents (id, title, subject, source_path, pages, indexed_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    subject = excluded.subject,
                    source_path = excluded.source_path,
                    pages = excluded.pages,
                    indexed_at = excluded.indexed_at
                """,
                (document_id, title, subject, source_path, pages, indexed_at_value),
            )
            connection.execute(
                """
                INSERT INTO chunks (id, document_id, page, text, chunk_index)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    document_id = excluded.document_id,
                    page = excluded.page,
                    text = excluded.text,
                    chunk_index = excluded.chunk_index
                """,
                (chunk_id, document_id, page, text, chunk_index),
            )
            connection.execute(
                """
                INSERT OR REPLACE INTO chunk_vec (chunk_id, embedding)
                VALUES (?, ?)
                """,
                (chunk_id, vector),
            )
    except (sqlite3.Error, OSError) as exc:
        raise RAGStoreError("failed to insert RAG chunk") from exc


def query_nearest(
    query_vec: Sequence[float],
    subject: str,
    top_k: int,
    *,
    db_path: Path | None = None,
) -> list[TextbookChunk]:
    """Return nearest chunks for a subject, sorted by cosine distance."""

    if top_k <= 0:
        return []
    vector = _serialize_embedding(query_vec)
    try:
        with _connect_vec(db_path) as connection:
            _ensure_schema(connection)
            rows = connection.execute(
                """
                SELECT
                    c.id,
                    c.document_id,
                    d.title,
                    d.subject,
                    d.source_path,
                    c.page,
                    c.text,
                    c.chunk_index,
                    vec_distance_cosine(v.embedding, ?) AS distance
                FROM chunks c
                JOIN chunk_vec v ON v.chunk_id = c.id
                JOIN documents d ON d.id = c.document_id
                WHERE d.subject = ?
                ORDER BY distance ASC
                LIMIT ?
                """,
                (vector, subject, top_k),
            ).fetchall()
    except (sqlite3.Error, OSError) as exc:
        raise RAGStoreError("failed to query RAG chunks") from exc
    return [_chunk_from_row(row) for row in rows]


def _connect_vec(db_path: Path | None) -> sqlite3.Connection:
    _check_sqlite_version()
    connection = connect(db_path)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.enable_load_extension(True)
    try:
        sqlite_vec.load(connection)
    finally:
        connection.enable_load_extension(False)
    return connection


def _ensure_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA)


def _check_sqlite_version() -> None:
    version = tuple(int(part) for part in sqlite3.sqlite_version.split(".")[:3])
    if version < MIN_SQLITE_VERSION:
        required = ".".join(str(part) for part in MIN_SQLITE_VERSION)
        raise RAGStoreError(
            f"sqlite >= {required} is required for sqlite-vec, got {sqlite3.sqlite_version}"
        )


def _serialize_embedding(embedding: Sequence[float]) -> bytes:
    try:
        values = [float(value) for value in embedding]
    except (TypeError, ValueError) as exc:
        raise RAGStoreError("embedding contains non-numeric values") from exc
    if len(values) != EMBEDDING_DIMENSION:
        raise RAGStoreError(
            f"embedding dimension must be {EMBEDDING_DIMENSION}, got {len(values)}"
        )
    return cast(bytes, sqlite_vec.serialize_float32(values))


def _chunk_from_row(row: sqlite3.Row) -> TextbookChunk:
    return TextbookChunk(
        id=str(row["id"]),
        document_id=str(row["document_id"]),
        title=str(row["title"]),
        subject=str(row["subject"]),
        source_path=str(row["source_path"]),
        page=_optional_int(row["page"]),
        text=str(row["text"]),
        chunk_index=int(row["chunk_index"]),
        distance=float(row["distance"]),
    )


def _document_from_row(row: sqlite3.Row) -> IndexedDocument:
    return IndexedDocument(
        id=str(row["id"]),
        title=str(row["title"]),
        subject=str(row["subject"]),
        source_path=str(row["source_path"]),
        pages=_optional_int(row["pages"]),
        indexed_at=str(row["indexed_at"]),
    )


def _optional_int(value: Any) -> int | None:
    return None if value is None else int(value)
