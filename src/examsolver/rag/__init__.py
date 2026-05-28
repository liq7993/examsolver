"""RAG helpers."""

from examsolver.rag.chunker import (
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    Chunk,
    chunk_pdf_pages,
    chunk_text,
)
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
    "DEFAULT_CHUNK_OVERLAP",
    "DEFAULT_CHUNK_SIZE",
    "DEFAULT_EMBED_MODEL",
    "EMBEDDING_DIMENSION",
    "Chunk",
    "EmbedderError",
    "SentenceTransformerEmbedder",
    "chunk_pdf_pages",
    "chunk_text",
    "embed",
    "embed_batch",
    "get_embedder",
]
