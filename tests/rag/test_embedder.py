from __future__ import annotations

import sys
from collections.abc import Generator, Sequence
from types import ModuleType
from typing import Any

import pytest

from examsolver.rag import embedder
from examsolver.rag.embedder import (
    EMBEDDING_DIMENSION,
    EmbedderError,
    SentenceTransformerEmbedder,
)


def _vector_for(text: str) -> list[float]:
    seed = float(sum(ord(char) for char in text) % 17)
    return [seed + float(index) / 1000.0 for index in range(EMBEDDING_DIMENSION)]


class FakeSentenceTransformer:
    constructed_with: list[str] = []

    def __init__(self, model_name_or_path: str) -> None:
        self.constructed_with.append(model_name_or_path)

    def encode(
        self,
        sentences: str | Sequence[str],
        *,
        normalize_embeddings: bool,
        show_progress_bar: bool,
    ) -> list[float] | list[list[float]]:
        assert normalize_embeddings is True
        assert show_progress_bar is False
        if isinstance(sentences, str):
            return _vector_for(sentences)
        return [_vector_for(text) for text in sentences]


@pytest.fixture(autouse=True)
def reset_embedder() -> Generator[None]:
    embedder._reset_for_tests()
    FakeSentenceTransformer.constructed_with = []
    yield
    embedder._reset_for_tests()


def test_singleton_is_lazy_and_uses_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_module = ModuleType("sentence_transformers")
    setattr(fake_module, "SentenceTransformer", FakeSentenceTransformer)
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)
    monkeypatch.setenv("EXAMSOLVER_EMBED_MODEL", "/models/local-embedder")

    singleton = embedder.get_embedder()

    assert singleton.is_loaded is False
    assert singleton.model_name_or_path == "/models/local-embedder"
    assert FakeSentenceTransformer.constructed_with == []

    vector = singleton.embed("齿轮公差")

    assert len(vector) == EMBEDDING_DIMENSION
    assert singleton.is_loaded is True
    assert FakeSentenceTransformer.constructed_with == ["/models/local-embedder"]
    assert embedder.get_embedder() is singleton


def test_default_model_is_multilingual_minilm(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_module = ModuleType("sentence_transformers")
    setattr(fake_module, "SentenceTransformer", FakeSentenceTransformer)
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)
    monkeypatch.delenv("EXAMSOLVER_EMBED_MODEL", raising=False)

    vector = embedder.embed("求导")

    assert len(vector) == 384
    assert FakeSentenceTransformer.constructed_with == [
        "paraphrase-multilingual-MiniLM-L12-v2"
    ]


def test_embed_batch_matches_individual_embeddings() -> None:
    model = FakeSentenceTransformer("fake")
    instance = SentenceTransformerEmbedder(model=model)
    texts = ["齿轮公差", "求 x^2 的导数"]

    batch = instance.embed_batch(texts)

    assert len(batch) == 2
    assert all(len(vector) == 384 for vector in batch)
    assert batch == [instance.embed(text) for text in texts]


def test_rejects_wrong_embedding_dimension() -> None:
    class BadModel:
        def encode(self, *args: Any, **kwargs: Any) -> list[float]:
            return [1.0, 2.0]

    instance = SentenceTransformerEmbedder(model=BadModel())

    with pytest.raises(EmbedderError, match="embedding dimension must be 384"):
        instance.embed("bad")
