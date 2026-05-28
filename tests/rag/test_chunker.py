from __future__ import annotations

import pytest

from examsolver.rag.chunker import Chunk, chunk_pdf_pages, chunk_text


def test_long_text_splits_by_character_count_with_overlap() -> None:
    text = "".join(str(index % 10) for index in range(1200))

    chunks = chunk_text(text, size=500, overlap=100)

    assert [len(chunk) for chunk in chunks] == [500, 500, 400]
    assert chunks[0][-100:] == chunks[1][:100]
    assert chunks[1][-100:] == chunks[2][:100]


def test_paragraph_separator_is_hard_boundary() -> None:
    first = "甲" * 320
    second = "乙" * 320

    chunks = chunk_text(f"{first}\n\n{second}", size=500, overlap=100)

    assert chunks == [first, second]


def test_heading_line_is_hard_boundary() -> None:
    intro = "绪论" * 80
    section = "齿轮公差" * 80

    chunks = chunk_text(f"{intro}\n# 第二章 公差\n{section}", size=500, overlap=100)

    assert chunks == [intro, "# 第二章 公差", section]


def test_chunk_pdf_pages_returns_one_based_page_and_global_index() -> None:
    chunks = chunk_pdf_pages(["第一页", "甲" * 650])

    assert chunks == [
        Chunk(page=1, chunk_index=0, text="第一页"),
        Chunk(page=2, chunk_index=1, text="甲" * 500),
        Chunk(page=2, chunk_index=2, text="甲" * 250),
    ]


def test_invalid_window_rejected() -> None:
    with pytest.raises(ValueError, match="overlap must be smaller"):
        chunk_text("text", size=100, overlap=100)
