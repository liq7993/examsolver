"""RAG helpers."""

from examsolver.rag.embedder import (
    DEFAULT_EMBED_MODEL,
    EMBEDDING_DIMENSION,
    EmbedderError,
    SentenceTransformerEmbedder,
    embed,
    embed_batch,
    get_embedder,
)

__all__ = [
    "DEFAULT_EMBED_MODEL",
    "EMBEDDING_DIMENSION",
    "EmbedderError",
    "SentenceTransformerEmbedder",
    "embed",
    "embed_batch",
    "get_embedder",
]
