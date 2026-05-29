"""Index a textbook PDF into the Examsolver RAG SQLite store."""

from __future__ import annotations

import argparse
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import cast
from uuid import NAMESPACE_URL, uuid5

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pypdf import PdfReader  # noqa: E402

from examsolver.multimodal import OCRError  # noqa: E402
from examsolver.multimodal.ocr_paddle import recognize  # noqa: E402
from examsolver.rag.chunker import Chunk, chunk_pdf_pages  # noqa: E402
from examsolver.rag.embedder import embed_batch  # noqa: E402
from examsolver.rag.store_sqlite_vec import (  # noqa: E402
    delete_document_by_source_path,
    get_document_by_source_path,
    init_schema,
    insert_chunk,
)

MIN_TEXT_CHARS_PER_PAGE = 20
OCR_EMPTY_PAGE_RATIO = 0.99
OCR_RENDER_SCALE = 2.0


@dataclass(frozen=True, slots=True)
class IndexStats:
    """Summary printed after indexing completes."""

    pages: int
    chunks: int
    elapsed_seconds: float
    errors: list[str]


def main() -> None:
    args = _parse_args()
    try:
        stats = index_textbook(
            pdf_path=args.pdf_path,
            subject=args.subject,
            title=args.title,
            force=args.force,
        )
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print(
        "Indexed "
        f"pages={stats.pages} chunks={stats.chunks} "
        f"elapsed={stats.elapsed_seconds:.2f}s errors={len(stats.errors)}"
    )
    for error in stats.errors:
        print(f"warning: {error}", file=sys.stderr)


def index_textbook(
    *,
    pdf_path: Path,
    subject: str,
    title: str,
    document_id: str | None = None,
    force: bool = False,
) -> IndexStats:
    """Read, chunk, embed, and store one textbook PDF."""

    started = time.perf_counter()
    resolved_pdf = pdf_path.expanduser().resolve()
    if not resolved_pdf.exists():
        raise RuntimeError(f"PDF does not exist: {resolved_pdf}")

    source_path = str(resolved_pdf)
    init_schema()
    existing = get_document_by_source_path(source_path)
    if existing is not None and not force:
        raise RuntimeError(
            f"{source_path} is already indexed as {existing.id}; rerun with --force to overwrite"
        )
    if existing is not None and force:
        delete_document_by_source_path(source_path)

    pages, errors = _read_pdf_pages(resolved_pdf)
    chunks = chunk_pdf_pages(pages)
    if not chunks:
        raise RuntimeError("no chunks were produced from the PDF")

    resolved_document_id = document_id or _document_id(source_path=source_path, subject=subject)
    embeddings = _embed_chunks(chunks)
    if len(embeddings) != len(chunks):
        raise RuntimeError("embedding count does not match chunk count")

    for index, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=True), start=1):
        _print_progress("write", index, len(chunks))
        insert_chunk(
            document_id=resolved_document_id,
            title=title,
            subject=subject,
            source_path=source_path,
            pages=len(pages),
            chunk_id=f"{resolved_document_id}:{chunk.chunk_index:06d}",
            page=chunk.page,
            text=chunk.text,
            chunk_index=chunk.chunk_index,
            embedding=embedding,
        )

    return IndexStats(
        pages=len(pages),
        chunks=len(chunks),
        elapsed_seconds=time.perf_counter() - started,
        errors=errors,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Index a PDF textbook into Examsolver RAG.")
    parser.add_argument("pdf_path", type=Path)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--force", action="store_true", help="Overwrite an existing source_path.")
    return parser.parse_args()


def _read_pdf_pages(pdf_path: Path) -> tuple[list[str], list[str]]:
    try:
        text_pages = _extract_text_pages(pdf_path)
    except RuntimeError as exc:
        print(f"pypdf text extraction failed; falling back to OCR: {exc}")
        return _ocr_pdf_pages(pdf_path, page_count=None)
    if not _needs_ocr(text_pages):
        print(f"Using embedded PDF text from {len(text_pages)} pages.")
        return text_pages, []

    print("Embedded PDF text is sparse; falling back to PaddleOCR page by page.")
    return _ocr_pdf_pages(pdf_path, page_count=len(text_pages))


def _extract_text_pages(pdf_path: Path) -> list[str]:
    try:
        reader = PdfReader(pdf_path)
        return [_repair_pdf_text((page.extract_text() or "").strip()) for page in reader.pages]
    except Exception as exc:
        raise RuntimeError(f"failed to read PDF text with pypdf: {pdf_path}") from exc


def _repair_pdf_text(text: str) -> str:
    try:
        repaired = text.encode("latin-1").decode("utf-8", errors="ignore")
    except UnicodeError:
        return text
    if _mojibake_score(repaired) < _mojibake_score(text):
        return repaired
    return text


def _mojibake_score(text: str) -> int:
    markers = "ÃÂâäåæçèéïðþÿ"
    return sum(text.count(marker) for marker in markers)


def _needs_ocr(pages: list[str]) -> bool:
    if not pages:
        return True
    empty_pages = sum(1 for page in pages if len(page.strip()) < MIN_TEXT_CHARS_PER_PAGE)
    return empty_pages / len(pages) >= OCR_EMPTY_PAGE_RATIO


def _ocr_pdf_pages(pdf_path: Path, *, page_count: int | None) -> tuple[list[str], list[str]]:
    try:
        import pypdfium2 as pdfium  # type: ignore[import-untyped]
    except Exception as exc:
        raise RuntimeError("OCR fallback requires pypdfium2 to render PDF pages") from exc

    with tempfile.TemporaryDirectory(prefix="examsolver-ocr-") as tmp_dir:
        document = pdfium.PdfDocument(str(pdf_path))
        resolved_page_count = page_count if page_count is not None else len(document)
        pages = [""] * resolved_page_count
        errors: list[str] = []
        for page_index in range(resolved_page_count):
            try:
                image_path = _render_pdf_page(document, page_index, Path(tmp_dir))
                result = recognize([image_path])
                pages[page_index] = result.text.strip()
            except (OCRError, OSError, RuntimeError) as exc:
                errors.append(f"page {page_index + 1}: {exc}")
                pages[page_index] = ""
            _print_progress("ocr", page_index + 1, resolved_page_count)
    return pages, errors


def _render_pdf_page(document: object, page_index: int, output_dir: Path) -> Path:
    page = document[page_index]  # type: ignore[index]
    bitmap = page.render(scale=OCR_RENDER_SCALE)
    image = bitmap.to_pil()
    image_path = output_dir / f"page-{page_index + 1:04d}.png"
    image.save(image_path)
    return image_path


def _embed_chunks(chunks: list[Chunk]) -> list[list[float]]:
    print(f"Embedding {len(chunks)} chunks.")
    embeddings = embed_batch([chunk.text for chunk in chunks])
    print("Embedding complete.")
    return cast(list[list[float]], embeddings)


def _document_id(*, source_path: str, subject: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"examsolver:textbook:{subject}:{source_path}"))


def _print_progress(label: str, current: int, total: int) -> None:
    if total <= 0:
        return
    if current == total or current == 1 or current % max(1, total // 10) == 0:
        percent = current / total * 100.0
        print(f"{label}: {current}/{total} ({percent:.0f}%)", flush=True)


if __name__ == "__main__":
    main()
