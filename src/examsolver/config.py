"""Minimal runtime configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def database_path() -> Path:
    """Return the SQLite database path, overridable for tests and deployments."""

    configured = os.environ.get("EXAMSOLVER_DB_PATH")
    if configured:
        return Path(configured)
    return Path("data") / "examsolver.db"


@dataclass(frozen=True, slots=True)
class LLMConfig:
    """Runtime configuration for the optional local explanation LLM."""

    provider: str
    base_url: str
    model: str
    model_path: Path | None
    timeout_seconds: float
    max_tokens: int
    temperature: float

    @property
    def enabled(self) -> bool:
        return self.provider == "local_gguf" and bool(self.base_url and self.model)

    @property
    def model_path_exists(self) -> bool:
        return self.model_path is not None and self.model_path.exists()


def load_llm_config() -> LLMConfig:
    """Load optional local Gemma/OpenAI-compatible LLM settings from env."""

    model_path_text = os.environ.get(
        "EXAMSOLVER_LLM_MODEL_PATH",
        "/mnt/e/gemma 4/gemma-4-E2B-it-Q4_K_M.gguf",
    )
    model_path = Path(model_path_text) if model_path_text else None
    return LLMConfig(
        provider=os.environ.get("EXAMSOLVER_LLM_PROVIDER", "none"),
        base_url=os.environ.get("EXAMSOLVER_LLM_BASE_URL", "http://127.0.0.1:8080/v1"),
        model=os.environ.get("EXAMSOLVER_LLM_MODEL", "gemma-4-E2B-it-Q4_K_M"),
        model_path=model_path,
        timeout_seconds=_env_float("EXAMSOLVER_LLM_TIMEOUT_SECONDS", 60.0),
        max_tokens=_env_int("EXAMSOLVER_LLM_MAX_TOKENS", 256),
        temperature=_env_float("EXAMSOLVER_LLM_TEMPERATURE", 0.2),
    )


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except ValueError:
        return default
