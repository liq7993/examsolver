"""Local LLM status route."""

from __future__ import annotations

from fastapi import APIRouter

from examsolver.api.schemas import LLMStatusBody
from examsolver.services.explanation import llm_status

router = APIRouter(tags=["llm"])


@router.get("/llm/status", response_model=LLMStatusBody)
def local_llm_status() -> LLMStatusBody:
    """Return configuration and short-probe status for local Gemma."""

    status = llm_status()
    return LLMStatusBody.model_validate(status)
