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
from examsolver.rag.retriever import (
    COSINE_DISTANCE_THRESHOLD,
    DEFAULT_TOP_K,
    TextbookChunk,
    retrieve,
)

__all__ = [
    "DEFAULT_CHUNK_OVERLAP",
    "DEFAULT_CHUNK_SIZE",
    "DEFAULT_EMBED_MODEL",
    "EMBEDDING_DIMENSION",
    "COSINE_DISTANCE_THRESHOLD",
    "DEFAULT_TOP_K",
    "Chunk",
    "EmbedderError",
    "SentenceTransformerEmbedder",
    "TextbookChunk",
    "chunk_pdf_pages",
    "chunk_text",
    "embed",
    "embed_batch",
    "get_embedder",
    "retrieve",
]
