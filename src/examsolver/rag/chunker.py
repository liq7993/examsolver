"""Character-based chunking helpers for RAG textbook indexing."""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 100


@dataclass(frozen=True, slots=True)
class Chunk:
    """A page-local text chunk ready for indexing."""

    page: int
    chunk_index: int
    text: str


def chunk_text(
    text: str,
    *,
    size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[str]:
    """Split text into character-counted chunks without crossing hard boundaries."""

    _validate_window(size=size, overlap=overlap)
    chunks: list[str] = []
    for block in _hard_blocks(text):
        chunks.extend(_chunk_block(block, size=size, overlap=overlap))
    return chunks


def chunk_pdf_pages(pages: list[str]) -> list[Chunk]:
    """Chunk PDF page text using 1-based page numbers and global chunk indexes."""

    chunks: list[Chunk] = []
    for page_index, page_text in enumerate(pages, start=1):
        for text in chunk_text(page_text):
            chunks.append(Chunk(page=page_index, chunk_index=len(chunks), text=text))
    return chunks


def _validate_window(*, size: int, overlap: int) -> None:
    if size <= 0:
        raise ValueError("chunk size must be positive")
    if overlap < 0:
        raise ValueError("chunk overlap must be non-negative")
    if overlap >= size:
        raise ValueError("chunk overlap must be smaller than chunk size")


def _hard_blocks(text: str) -> list[str]:
    blocks: list[str] = []
    current_lines: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            _flush_current(blocks, current_lines)
            continue
        if stripped.startswith("#"):
            _flush_current(blocks, current_lines)
            blocks.append(stripped)
            continue
        current_lines.append(line)

    _flush_current(blocks, current_lines)
    return blocks


def _flush_current(blocks: list[str], current_lines: list[str]) -> None:
    if not current_lines:
        return
    block = "\n".join(current_lines).strip()
    current_lines.clear()
    if block:
        blocks.append(block)


def _chunk_block(block: str, *, size: int, overlap: int) -> list[str]:
    if len(block) <= size:
        return [block]

    step = size - overlap
    chunks: list[str] = []
    start = 0
    while start < len(block):
        chunk = block[start : start + size]
        if chunk:
            chunks.append(chunk)
        if start + size >= len(block):
            break
        start += step
    return chunks
