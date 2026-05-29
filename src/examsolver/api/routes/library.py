"""Textbook library routes."""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from types import ModuleType
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from examsolver.storage.documents_repo import (
    DocumentRecord,
    create_document,
    delete_document,
    get_document,
    list_documents,
)

PROJECT_ROOT = Path(__file__).resolve().parents[4]
TEXTBOOK_DIR = PROJECT_ROOT / "data" / "textbooks"
INDEX_SCRIPT_PATH = PROJECT_ROOT / "scripts" / "index_textbook.py"
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024

logger = logging.getLogger(__name__)
router = APIRouter(tags=["library"])


class LibraryDocumentBody(BaseModel):
    """HTTP representation of one library document."""

    id: str
    title: str
    subject: str
    source_path: str
    pages: int | None
    indexed_at: str
    chunk_count: int
    indexed: bool

    @classmethod
    def from_record(cls, record: DocumentRecord) -> "LibraryDocumentBody":
        return cls(
            id=record.id,
            title=record.title,
            subject=record.subject,
            source_path=record.source_path,
            pages=record.pages,
            indexed_at=record.indexed_at,
            chunk_count=record.chunk_count,
            indexed=record.indexed,
        )


class LibraryListBody(BaseModel):
    """Textbook library list response."""

    documents: list[LibraryDocumentBody]


class LibraryUploadBody(BaseModel):
    """Upload response with the created document id."""

    document_id: str = Field(description="Created documents.id value")
    document: LibraryDocumentBody


class LibraryIndexBody(BaseModel):
    """Synchronous indexing response."""

    document_id: str
    pages: int
    chunks: int
    elapsed_seconds: float
    errors: list[str]
    document: LibraryDocumentBody


@router.get("/library", response_model=LibraryListBody)
def library() -> LibraryListBody:
    """List uploaded and indexed textbook documents."""

    return LibraryListBody(
        documents=[LibraryDocumentBody.from_record(record) for record in list_documents()]
    )


@router.post("/library/upload", response_model=LibraryUploadBody)
async def upload_textbook(
    file: UploadFile = File(...),
    subject: str = Form(...),
    title: str = Form(...),
) -> LibraryUploadBody:
    """Store one uploaded PDF under the controlled textbook directory."""

    subject_value = subject.strip()
    title_value = title.strip()
    if not subject_value:
        raise HTTPException(status_code=400, detail="subject is required")
    if not title_value:
        raise HTTPException(status_code=400, detail="title is required")
    if Path(file.filename or "").suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="only PDF uploads are supported")

    document_id = str(uuid4())
    TEXTBOOK_DIR.mkdir(parents=True, exist_ok=True)
    destination = (TEXTBOOK_DIR / f"{document_id}.pdf").resolve()
    _assert_textbook_path(destination)

    bytes_written = 0
    try:
        with destination.open("wb") as output:
            while chunk := await file.read(CHUNK_SIZE):
                bytes_written += len(chunk)
                if bytes_written > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="PDF upload exceeds 50MB limit")
                output.write(chunk)
        if bytes_written == 0:
            raise HTTPException(status_code=400, detail="uploaded PDF is empty")
        record = create_document(
            document_id=document_id,
            title=title_value,
            subject=subject_value,
            source_path=str(destination),
        )
    except HTTPException:
        destination.unlink(missing_ok=True)
        raise
    except Exception as exc:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="failed to save uploaded PDF") from exc
    finally:
        await file.close()

    return LibraryUploadBody(
        document_id=document_id,
        document=LibraryDocumentBody.from_record(record),
    )


@router.post("/library/index/{doc_id}", response_model=LibraryIndexBody)
def index_library_document(doc_id: str) -> LibraryIndexBody:
    """Synchronously index one uploaded textbook PDF."""

    record = get_document(doc_id)
    if record is None:
        raise HTTPException(status_code=404, detail="document_id not found")
    pdf_path = Path(record.source_path).resolve()
    _assert_textbook_path(pdf_path)
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="uploaded PDF file not found")

    logger.info("library.index begin document_id=%s subject=%s", doc_id, record.subject)
    try:
        stats = _index_textbook(
            pdf_path=pdf_path,
            subject=record.subject,
            title=record.title,
            document_id=record.id,
        )
    except RuntimeError as exc:
        logger.warning("library.index failed document_id=%s error=%s", doc_id, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    refreshed = get_document(doc_id)
    if refreshed is None:
        raise HTTPException(status_code=500, detail="indexed document metadata missing")
    logger.info(
        "library.index done document_id=%s pages=%s chunks=%s",
        doc_id,
        stats.pages,
        stats.chunks,
    )
    return LibraryIndexBody(
        document_id=doc_id,
        pages=stats.pages,
        chunks=stats.chunks,
        elapsed_seconds=stats.elapsed_seconds,
        errors=stats.errors,
        document=LibraryDocumentBody.from_record(refreshed),
    )


@router.delete("/library/{doc_id}", response_model=LibraryDocumentBody)
def delete_library_document(doc_id: str) -> LibraryDocumentBody:
    """Delete one library document and its uploaded PDF if it is managed by Examsolver."""

    record = delete_document(doc_id)
    if record is None:
        raise HTTPException(status_code=404, detail="document_id not found")
    pdf_path = Path(record.source_path).resolve()
    _assert_textbook_path(pdf_path)
    pdf_path.unlink(missing_ok=True)
    return LibraryDocumentBody.from_record(record)


def _assert_textbook_path(path: Path) -> None:
    textbook_root = TEXTBOOK_DIR.resolve()
    if path != textbook_root and textbook_root not in path.parents:
        raise HTTPException(status_code=400, detail="document path is outside textbook storage")


def _index_textbook(
    *,
    pdf_path: Path,
    subject: str,
    title: str,
    document_id: str,
) -> Any:
    module = _load_index_script()
    return module.index_textbook(
        pdf_path=pdf_path,
        subject=subject,
        title=title,
        document_id=document_id,
        force=True,
    )


def _load_index_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("examsolver_index_textbook", INDEX_SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load index_textbook script")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
