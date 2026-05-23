"""Health, readiness, and runtime info routes for the HTTP shell."""

from __future__ import annotations

import os
import time
from importlib.metadata import PackageNotFoundError, version
from typing import Any

from fastapi import APIRouter, Response, status

from examsolver.config import database_path
from examsolver.skills.base import PersistenceError
from examsolver.skills.registry import all_skills
from examsolver.storage.db import connect

router = APIRouter(tags=["health"])
_STARTED_AT = time.monotonic()


@router.get("/health")
def health() -> dict[str, str]:
    """Return a minimal liveness signal."""

    return {"status": "ok"}


@router.get("/ready")
def ready(response: Response) -> dict[str, Any]:
    """Return dependency readiness for deployment probes."""

    skills = all_skills()
    registry_ok = len(skills) > 0
    database_ok = True
    database_error: str | None = None

    try:
        with connect() as connection:
            connection.execute("SELECT 1").fetchone()
    except PersistenceError as exc:
        database_ok = False
        database_error = str(exc)

    is_ready = registry_ok and database_ok
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    checks: dict[str, Any] = {
        "database": {
            "ok": database_ok,
            "path": str(database_path()),
        },
        "registry": {
            "ok": registry_ok,
            "skill_count": len(skills),
        },
    }
    if database_error is not None:
        checks["database"]["error"] = database_error

    return {
        "status": "ready" if is_ready else "not_ready",
        "checks": checks,
    }


@router.get("/info")
def info() -> dict[str, Any]:
    """Return a small runtime snapshot for debugging."""

    skills = all_skills()
    return {
        "name": "Examsolver",
        "version": _package_version(),
        "git_sha": os.environ.get("EXAMSOLVER_GIT_SHA", "unknown"),
        "uptime_seconds": round(time.monotonic() - _STARTED_AT, 3),
        "skill_count": len(skills),
        "skills": [skill.name for skill in skills],
        "database_path": str(database_path()),
    }


def _package_version() -> str:
    try:
        return version("examsolver")
    except PackageNotFoundError:
        return "0.0.1"
