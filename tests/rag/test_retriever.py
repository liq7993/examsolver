from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from examsolver.rag import retriever
from examsolver.rag.embedder import EmbedderError
from examsolver.rag.store_sqlite_vec import TextbookChunk as StoredTextbookChunk


def test_retrieve_returns_hits_under_cosine_distance_threshold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    query_vectors: list[list[float]] = []
    calls: list[tuple[list[float], str, int]] = []

    def fake_embed(query: str) -> list[float]:
        assert query == "导数定义"
        query_vectors.append([1.0, 0.0])
        return [1.0, 0.0]

    def fake_query_nearest(
        query_vec: Sequence[float],
        subject: str,
        top_k: int,
        *,
        db_path: Path | None = None,
    ) -> list[StoredTextbookChunk]:
        calls.append((list(query_vec), subject, top_k))
        return [
            StoredTextbookChunk(
                id="chunk-1",
                document_id="doc-1",
                title="Calculus",
                subject="math",
                source_path="/books/calculus.pdf",
                page=3,
                text="导数是函数变化率。",
                chunk_index=0,
                distance=0.12,
            ),
            StoredTextbookChunk(
                id="chunk-2",
                document_id="doc-1",
                title="Calculus",
                subject="math",
                source_path="/books/calculus.pdf",
                page=4,
                text="积分用于累积。",
                chunk_index=1,
                distance=0.72,
            ),
        ]

    monkeypatch.setattr(retriever, "embed", fake_embed)
    monkeypatch.setattr(retriever, "query_nearest", fake_query_nearest)

    chunks = retriever.retrieve("导数定义", "math", top_k=5)

    assert calls == [([1.0, 0.0], "math", 5)]
    assert len(chunks) == 1
    assert chunks[0] == retriever.TextbookChunk(
        id="chunk-1",
        document_id="doc-1",
        document_title="Calculus",
        subject="math",
        page=3,
        text="导数是函数变化率。",
        score=0.12,
    )


def test_retrieve_returns_empty_when_all_distances_miss(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(retriever, "embed", lambda query: [1.0, 0.0])
    monkeypatch.setattr(
        retriever,
        "query_nearest",
        lambda query_vec, subject, top_k, *, db_path=None: [
            StoredTextbookChunk(
                id="chunk-miss",
                document_id="doc-1",
                title="Calculus",
                subject="math",
                source_path="/books/calculus.pdf",
                page=1,
                text="不相关内容",
                chunk_index=0,
                distance=0.5,
            )
        ],
    )

    assert retriever.retrieve("导数定义", "math") == []


def test_retrieve_keeps_cross_subject_isolation(monkeypatch: pytest.MonkeyPatch) -> None:
    seen_subjects: list[str] = []

    monkeypatch.setattr(retriever, "embed", lambda query: [1.0, 0.0])

    def fake_query_nearest(
        query_vec: Sequence[float],
        subject: str,
        top_k: int,
        *,
        db_path: Path | None = None,
    ) -> list[StoredTextbookChunk]:
        seen_subjects.append(subject)
        if subject != "physics":
            return []
        return [
            StoredTextbookChunk(
                id="physics-chunk",
                document_id="doc-physics",
                title="Mechanics",
                subject="physics",
                source_path="/books/mechanics.pdf",
                page=2,
                text="受力平衡。",
                chunk_index=0,
                distance=0.2,
            )
        ]

    monkeypatch.setattr(retriever, "query_nearest", fake_query_nearest)

    assert retriever.retrieve("受力", "math") == []
    physics_chunks = retriever.retrieve("受力", "physics")

    assert seen_subjects == ["math", "physics"]
    assert [chunk.subject for chunk in physics_chunks] == ["physics"]
    assert [chunk.document_id for chunk in physics_chunks] == ["doc-physics"]


def test_retrieve_degrades_to_empty_on_runtime_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken_embed(query: str) -> list[float]:
        raise EmbedderError("model unavailable")

    monkeypatch.setattr(retriever, "embed", broken_embed)

    assert retriever.retrieve("导数定义", "math") == []
    assert retriever.retrieve("", "math") == []
    assert retriever.retrieve("导数定义", "", top_k=5) == []
    assert retriever.retrieve("导数定义", "math", top_k=0) == []
