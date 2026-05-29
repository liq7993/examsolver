"""Repository for textbook document metadata."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from examsolver.rag.store_sqlite_vec import (
    RAGStoreError,
    delete_document_by_source_path,
    init_schema,
)
from examsolver.skills.base import PersistenceError
from examsolver.storage.db import connect


@dataclass(frozen=True, slots=True)
class DocumentRecord:
    """Flat metadata row for library management."""

    id: str
    title: str
    subject: str
    source_path: str
    pages: int | None
    indexed_at: str
    chunk_count: int

    @property
    def indexed(self) -> bool:
        """Return whether this document has stored chunks."""

        return self.chunk_count > 0


def create_document(
    *,
    document_id: str,
    title: str,
    subject: str,
    source_path: str,
    pages: int | None = None,
    indexed_at: str = "",
    db_path: Path | None = None,
) -> DocumentRecord:
    """Create one uploaded document metadata row."""

    _ensure_documents_schema(db_path)
    try:
        with connect(db_path) as connection:
            connection.execute(
                """
                INSERT INTO documents (id, title, subject, source_path, pages, indexed_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (document_id, title, subject, source_path, pages, indexed_at),
            )
    except (sqlite3.Error, OSError) as exc:
        raise PersistenceError("failed to create document metadata") from exc
    document = get_document(document_id, db_path=db_path)
    if document is None:
        raise PersistenceError("created document metadata was not found")
    return document


def get_document(document_id: str, *, db_path: Path | None = None) -> DocumentRecord | None:
    """Return one document metadata row by id."""

    _ensure_documents_schema(db_path)
    try:
        with connect(db_path) as connection:
            row = connection.execute(
                """
                SELECT
                    d.id,
                    d.title,
                    d.subject,
                    d.source_path,
                    d.pages,
                    d.indexed_at,
                    COUNT(c.id) AS chunk_count
                FROM documents d
                LEFT JOIN chunks c ON c.document_id = d.id
                WHERE d.id = ?
                GROUP BY d.id
                """,
                (document_id,),
            ).fetchone()
    except (sqlite3.Error, OSError) as exc:
        raise PersistenceError("failed to fetch document metadata") from exc
    return None if row is None else _record_from_row(row)


def list_documents(*, db_path: Path | None = None) -> list[DocumentRecord]:
    """Return newest-first textbook library records."""

    _ensure_documents_schema(db_path)
    try:
        with connect(db_path) as connection:
            rows = connection.execute(
                """
                SELECT
                    d.id,
                    d.title,
                    d.subject,
                    d.source_path,
                    d.pages,
                    d.indexed_at,
                    COUNT(c.id) AS chunk_count
                FROM documents d
                LEFT JOIN chunks c ON c.document_id = d.id
                GROUP BY d.id
                ORDER BY d.indexed_at DESC, d.title ASC
                """
            ).fetchall()
    except (sqlite3.Error, OSError) as exc:
        raise PersistenceError("failed to list document metadata") from exc
    return [_record_from_row(row) for row in rows]


def delete_document(document_id: str, *, db_path: Path | None = None) -> DocumentRecord | None:
    """Delete one document and all indexed chunks/vectors."""

    document = get_document(document_id, db_path=db_path)
    if document is None:
        return None
    try:
        delete_document_by_source_path(document.source_path, db_path=db_path)
    except RAGStoreError as exc:
        raise PersistenceError("failed to delete document metadata") from exc
    return document


def _ensure_documents_schema(db_path: Path | None) -> None:
    try:
        init_schema(db_path=db_path)
    except RAGStoreError as exc:
        raise PersistenceError("failed to prepare document metadata schema") from exc


def _record_from_row(row: sqlite3.Row) -> DocumentRecord:
    return DocumentRecord(
        id=str(row["id"]),
        title=str(row["title"]),
        subject=str(row["subject"]),
        source_path=str(row["source_path"]),
        pages=None if row["pages"] is None else int(row["pages"]),
        indexed_at=str(row["indexed_at"]),
        chunk_count=int(row["chunk_count"]),
    )
