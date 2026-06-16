"""HTTP mapping for recoverable persistence failures."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from fastapi import HTTPException

from examsolver.skills.base import PersistenceError

T = TypeVar("T")


def repo_call(fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    try:
        return fn(*args, **kwargs)
    except PersistenceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
