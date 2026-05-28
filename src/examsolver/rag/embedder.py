"""sentence-transformers adapter with lazy singleton model loading."""

from __future__ import annotations

import os
from collections.abc import Sequence
from importlib import import_module
from threading import Lock
from typing import Any, Protocol, cast

DEFAULT_EMBED_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
EMBED_MODEL_ENV = "EXAMSOLVER_EMBED_MODEL"
EMBEDDING_DIMENSION = 384


class EmbedderError(RuntimeError):
    """Raised when embeddings cannot be produced."""


class _SentenceTransformerModel(Protocol):
    def encode(
        self,
        sentences: str | Sequence[str],
        *,
        normalize_embeddings: bool,
        show_progress_bar: bool,
    ) -> Any: ...


class SentenceTransformerEmbedder:
    """Thin synchronous wrapper around sentence-transformers."""

    def __init__(
        self,
        model_name_or_path: str | None = None,
        model: _SentenceTransformerModel | None = None,
    ) -> None:
        self.model_name_or_path = model_name_or_path or os.environ.get(
            EMBED_MODEL_ENV, DEFAULT_EMBED_MODEL
        )
        self._model = model

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def embed(self, text: str) -> list[float]:
        """Embed one string as a normalized 384-dimensional vector."""

        raw = self._load().encode(text, normalize_embeddings=True, show_progress_bar=False)
        return _coerce_vector(raw)

    def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed strings as normalized 384-dimensional vectors."""

        if not texts:
            return []
        raw = self._load().encode(
            list(texts), normalize_embeddings=True, show_progress_bar=False
        )
        rows = _coerce_rows(raw)
        return [_coerce_vector(row) for row in rows]

    def _load(self) -> _SentenceTransformerModel:
        if self._model is None:
            try:
                module = import_module("sentence_transformers")
                sentence_transformer = module.SentenceTransformer
            except Exception as exc:
                raise EmbedderError("sentence-transformers is not importable") from exc
            try:
                self._model = cast(
                    _SentenceTransformerModel,
                    sentence_transformer(self.model_name_or_path),
                )
            except Exception as exc:
                raise EmbedderError(
                    f"embedding model initialization failed: {self.model_name_or_path}"
                ) from exc
        return self._model


_EMBEDDER: SentenceTransformerEmbedder | None = None
_EMBEDDER_LOCK = Lock()


def get_embedder() -> SentenceTransformerEmbedder:
    """Return the process-wide lazy embedder singleton."""

    global _EMBEDDER
    if _EMBEDDER is None:
        with _EMBEDDER_LOCK:
            if _EMBEDDER is None:
                _EMBEDDER = SentenceTransformerEmbedder()
    return _EMBEDDER


def embed(text: str) -> list[float]:
    """Convenience function using the singleton embedder."""

    return get_embedder().embed(text)


def embed_batch(texts: Sequence[str]) -> list[list[float]]:
    """Convenience function using the singleton embedder."""

    return get_embedder().embed_batch(texts)


def _reset_for_tests() -> None:
    """Reset the singleton so tests can assert lazy loading behavior."""

    global _EMBEDDER
    with _EMBEDDER_LOCK:
        _EMBEDDER = None


def _coerce_rows(raw: Any) -> list[Any]:
    value = _tolist(raw)
    if not isinstance(value, list):
        raise EmbedderError("embedding batch output is not a list")
    return value


def _coerce_vector(raw: Any) -> list[float]:
    value = _tolist(raw)
    if not isinstance(value, list):
        raise EmbedderError("embedding output is not a list")
    try:
        vector = [float(item) for item in value]
    except (TypeError, ValueError) as exc:
        raise EmbedderError("embedding output contains non-numeric values") from exc
    if len(vector) != EMBEDDING_DIMENSION:
        raise EmbedderError(
            f"embedding dimension must be {EMBEDDING_DIMENSION}, got {len(vector)}"
        )
    return vector


def _tolist(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return value.tolist()
    return value
