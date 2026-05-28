"""Online RAG retrieval over indexed textbook chunks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from examsolver.rag.embedder import EmbedderError, embed
from examsolver.rag.store_sqlite_vec import (
    RAGStoreError,
    TextbookChunk as StoredTextbookChunk,
    query_nearest,
)

COSINE_DISTANCE_THRESHOLD = 0.5
DEFAULT_TOP_K = 5


@dataclass(frozen=True, slots=True)
class TextbookChunk:
    """Public retriever result used by graph and skills."""

    id: str
    document_id: str
    document_title: str
    subject: str
    page: int | None
    text: str
    score: float


def retrieve(
    query: str,
    subject: str,
    top_k: int = DEFAULT_TOP_K,
    *,
    db_path: Path | None = None,
) -> list[TextbookChunk]:
    """Retrieve nearest textbook chunks, returning an empty list on RAG misses."""

    if top_k <= 0 or not query.strip() or not subject.strip():
        return []
    try:
        query_vec = embed(query)
        rows = query_nearest(query_vec, subject, top_k, db_path=db_path)
    except (EmbedderError, RAGStoreError):
        return []
    return [_to_result(row) for row in rows if row.distance < COSINE_DISTANCE_THRESHOLD]


def _to_result(row: StoredTextbookChunk) -> TextbookChunk:
    return TextbookChunk(
        id=row.id,
        document_id=row.document_id,
        document_title=row.title,
        subject=row.subject,
        page=row.page,
        text=row.text,
        score=row.distance,
    )
