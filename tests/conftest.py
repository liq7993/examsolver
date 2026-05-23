from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_history_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("EXAMSOLVER_DB_PATH", str(tmp_path / "examsolver.db"))
