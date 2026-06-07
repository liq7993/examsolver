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


# Local LLM presets. Pick one with EXAMSOLVER_LLM_PRESET; any individual
# EXAMSOLVER_LLM_* env var still overrides the preset's default value.
#
# Adding a new preset = adding one entry. No code changes elsewhere.
# model_path defaults are intentionally empty. Set them per-environment via
# EXAMSOLVER_LLM_MODEL_PATH (single-value override) or by exporting the
# corresponding env var from your launcher script. An empty path leaves
# `model_path_exists` False, which the runtime treats as "local LLM disabled".
_LLM_PRESETS: dict[str, dict[str, str | float | int]] = {
    "gemma4": {
        "model": "gemma-4-E2B-it-Q4_K_M",
        "model_path": "",
        "timeout_seconds": 60.0,
        "max_tokens": 256,
        "temperature": 0.2,
    },
    "gpt-oss-20b": {
        "model": "gpt-oss-20b",
        "model_path": "",
        "timeout_seconds": 120.0,
        "max_tokens": 1024,
        "temperature": 0.2,
    },
    "gpt-oss-120b": {
        "model": "gpt-oss-120b",
        "model_path": "",
        "timeout_seconds": 240.0,
        "max_tokens": 2048,
        "temperature": 0.2,
    },
}
_DEFAULT_PRESET = "gemma4"


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
    preset: str = _DEFAULT_PRESET

    @property
    def enabled(self) -> bool:
        return self.provider == "local_gguf" and bool(self.base_url and self.model)

    @property
    def model_path_exists(self) -> bool:
        return self.model_path is not None and self.model_path.exists()


def load_llm_config() -> LLMConfig:
    """Load optional local OpenAI-compatible LLM settings from env.

    Preset chain:
        EXAMSOLVER_LLM_PRESET sets defaults (gemma4 / gpt-oss-20b / gpt-oss-120b).
        Per-key env vars (EXAMSOLVER_LLM_MODEL, _MODEL_PATH, _TIMEOUT_SECONDS,
        _MAX_TOKENS, _TEMPERATURE) override the preset's default.
    """

    preset_name = os.environ.get("EXAMSOLVER_LLM_PRESET", _DEFAULT_PRESET)
    preset = _LLM_PRESETS.get(preset_name, _LLM_PRESETS[_DEFAULT_PRESET])

    model_path_text = os.environ.get(
        "EXAMSOLVER_LLM_MODEL_PATH",
        str(preset["model_path"]),
    )
    model_path = Path(model_path_text) if model_path_text else None
    return LLMConfig(
        provider=os.environ.get("EXAMSOLVER_LLM_PROVIDER", "none"),
        base_url=os.environ.get("EXAMSOLVER_LLM_BASE_URL", "http://127.0.0.1:8080/v1"),
        model=os.environ.get("EXAMSOLVER_LLM_MODEL", str(preset["model"])),
        model_path=model_path,
        timeout_seconds=_env_float(
            "EXAMSOLVER_LLM_TIMEOUT_SECONDS", float(preset["timeout_seconds"])
        ),
        max_tokens=_env_int("EXAMSOLVER_LLM_MAX_TOKENS", int(preset["max_tokens"])),
        temperature=_env_float("EXAMSOLVER_LLM_TEMPERATURE", float(preset["temperature"])),
        preset=preset_name,
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
