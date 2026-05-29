from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

from examsolver.rag.chunker import Chunk
from examsolver.rag.store_sqlite_vec import IndexedDocument


SCRIPT_PATH = Path(__file__).parents[2] / "scripts" / "index_textbook.py"


@pytest.fixture()
def index_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("index_textbook", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_index_textbook_text_pdf_path_writes_chunks(
    index_script: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "tolerance.pdf"
    pdf_path.write_bytes(b"%PDF fake")
    inserted: list[dict[str, object]] = []

    monkeypatch.setattr(index_script, "init_schema", lambda: None)
    monkeypatch.setattr(index_script, "get_document_by_source_path", lambda source_path: None)
    monkeypatch.setattr(index_script, "_read_pdf_pages", lambda pdf_path: (["甲" * 650], []))
    monkeypatch.setattr(
        index_script,
        "embed_batch",
        lambda texts: [[float(index)] * 384 for index, _text in enumerate(texts)],
    )

    def fake_insert_chunk(**kwargs: object) -> None:
        inserted.append(kwargs)

    monkeypatch.setattr(index_script, "insert_chunk", fake_insert_chunk)

    stats = index_script.index_textbook(
        pdf_path=pdf_path,
        subject="tolerance",
        title="公差与测量",
    )

    assert stats.pages == 1
    assert stats.chunks == 2
    assert len(inserted) == 2
    assert inserted[0]["title"] == "公差与测量"
    assert inserted[0]["subject"] == "tolerance"
    assert inserted[0]["source_path"] == str(pdf_path.resolve())
    assert inserted[0]["page"] == 1
    assert inserted[0]["chunk_index"] == 0
    assert isinstance(inserted[0]["embedding"], list)


def test_duplicate_source_path_reuses_existing_index(
    index_script: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "tolerance.pdf"
    pdf_path.write_bytes(b"%PDF fake")
    existing = IndexedDocument(
        id="doc-1",
        title="公差与测量",
        subject="tolerance",
        source_path=str(pdf_path.resolve()),
        pages=12,
        indexed_at="2026-05-28T00:00:00+00:00",
    )

    monkeypatch.setattr(index_script, "init_schema", lambda: None)
    monkeypatch.setattr(index_script, "get_document_by_source_path", lambda source_path: existing)
    monkeypatch.setattr(index_script, "count_document_chunks", lambda document_id: 240)

    stats = index_script.index_textbook(
        pdf_path=pdf_path,
        subject="tolerance",
        title="公差与测量",
    )

    assert stats.pages == 12
    assert stats.chunks == 240
    assert stats.errors == []


def test_force_deletes_existing_source_before_writing(
    index_script: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "tolerance.pdf"
    pdf_path.write_bytes(b"%PDF fake")
    deleted: list[str] = []
    inserted: list[dict[str, object]] = []
    existing = IndexedDocument(
        id="doc-1",
        title="公差与测量",
        subject="tolerance",
        source_path=str(pdf_path.resolve()),
        pages=12,
        indexed_at="2026-05-28T00:00:00+00:00",
    )

    monkeypatch.setattr(index_script, "init_schema", lambda: None)
    monkeypatch.setattr(index_script, "get_document_by_source_path", lambda source_path: existing)
    monkeypatch.setattr(
        index_script,
        "delete_document_by_source_path",
        lambda source_path: _record_delete(deleted, source_path),
    )
    monkeypatch.setattr(
        index_script,
        "chunk_pdf_pages",
        lambda pages: [Chunk(page=1, chunk_index=0, text="甲" * 20)],
    )
    monkeypatch.setattr(index_script, "_read_pdf_pages", lambda pdf_path: (["甲" * 20], []))
    monkeypatch.setattr(index_script, "embed_batch", lambda texts: [[0.0] * 384])
    monkeypatch.setattr(index_script, "insert_chunk", lambda **kwargs: inserted.append(kwargs))

    stats = index_script.index_textbook(
        pdf_path=pdf_path,
        subject="tolerance",
        title="公差与测量",
        force=True,
    )

    assert deleted == [str(pdf_path.resolve())]
    assert stats.chunks == 1
    assert len(inserted) == 1


def _record_delete(deleted: list[str], source_path: str) -> int:
    deleted.append(source_path)
    return 1


def test_ocr_needed_only_when_nearly_all_pages_empty(index_script: ModuleType) -> None:
    assert index_script._needs_ocr(["", "", ""]) is True
    assert index_script._needs_ocr(["甲" * 20, "", ""]) is False


def test_repair_pdf_text_fixes_utf8_mojibake(index_script: ModuleType) -> None:
    mojibake = "H7é\x85\x8då\x90\x88"

    assert index_script._repair_pdf_text(mojibake) == "H7配合"
