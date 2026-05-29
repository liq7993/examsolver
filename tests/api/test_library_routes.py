from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from examsolver.api.app import create_app
from examsolver.api.routes import library as library_route


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    monkeypatch.setattr(library_route, "TEXTBOOK_DIR", tmp_path / "textbooks")
    return TestClient(create_app())


def test_library_upload_list_and_delete(client: TestClient, tmp_path: Path) -> None:
    response = client.post(
        "/library/upload",
        files={"file": ("tolerance.pdf", b"%PDF-1.4\n%%EOF\n", "application/pdf")},
        data={"subject": "tolerance", "title": "公差"},
    )

    assert response.status_code == 200
    body = response.json()
    document_id = body["document_id"]
    source_path = Path(body["document"]["source_path"])
    assert source_path.parent == tmp_path / "textbooks"
    assert source_path.exists()

    listed = client.get("/library")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["documents"]] == [document_id]

    deleted = client.delete(f"/library/{document_id}")
    assert deleted.status_code == 200
    assert deleted.json()["id"] == document_id
    assert not source_path.exists()
    assert client.get("/library").json()["documents"] == []


def test_library_upload_rejects_files_over_50mb(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(library_route, "MAX_UPLOAD_BYTES", 3)

    response = client.post(
        "/library/upload",
        files={"file": ("too-large.pdf", b"1234", "application/pdf")},
        data={"subject": "tolerance", "title": "公差"},
    )

    assert response.status_code == 413
    assert client.get("/library").json()["documents"] == []


def test_library_index_delegates_to_index_textbook(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    uploaded = client.post(
        "/library/upload",
        files={"file": ("tolerance.pdf", b"%PDF-1.4\n%%EOF\n", "application/pdf")},
        data={"subject": "tolerance", "title": "公差"},
    ).json()
    document_id = uploaded["document_id"]
    calls: list[dict[str, object]] = []

    def fake_index_textbook(**kwargs: object) -> SimpleNamespace:
        calls.append(kwargs)
        return SimpleNamespace(pages=1, chunks=2, elapsed_seconds=0.01, errors=[])

    monkeypatch.setattr(library_route, "_index_textbook", fake_index_textbook)

    response = client.post(f"/library/index/{document_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["document_id"] == document_id
    assert body["pages"] == 1
    assert body["chunks"] == 2
    assert calls == [
        {
            "pdf_path": Path(uploaded["document"]["source_path"]),
            "subject": "tolerance",
            "title": "公差",
            "document_id": document_id,
        }
    ]


def test_library_loads_index_script_module() -> None:
    module = library_route._load_index_script()

    assert hasattr(module, "index_textbook")
