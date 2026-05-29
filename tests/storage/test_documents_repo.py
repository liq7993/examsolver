from __future__ import annotations

from pathlib import Path

from examsolver.storage.documents_repo import (
    create_document,
    delete_document,
    get_document,
    list_documents,
)


def test_documents_repo_crud(tmp_path: Path) -> None:
    db_path = tmp_path / "examsolver.db"

    created = create_document(
        document_id="doc-1",
        title="公差",
        subject="tolerance",
        source_path=str(tmp_path / "book.pdf"),
        db_path=db_path,
    )
    listed = list_documents(db_path=db_path)
    fetched = get_document("doc-1", db_path=db_path)
    deleted = delete_document("doc-1", db_path=db_path)

    assert created.id == "doc-1"
    assert created.indexed is False
    assert listed == [created]
    assert fetched == created
    assert deleted == created
    assert get_document("doc-1", db_path=db_path) is None
    assert list_documents(db_path=db_path) == []
