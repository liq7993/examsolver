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


@dataclass(frozen=True, slots=True)
class CloudLLMProvider:
    """A cloud LLM reachable over the OpenAI-compatible chat-completions API."""

    name: str
    label: str
    base_url: str
    default_model: str
    api_key_env: str
    # Multimodal (vision) model for this provider, when known. Left None for
    # text-only providers; an env override (EXAMSOLVER_LLM_VISION_MODEL) wins so a
    # new vision model can be pointed at without a code change.
    vision_model: str | None = None


# Cloud providers that speak the OpenAI chat-completions wire format. Select one
# with EXAMSOLVER_LLM_PROVIDER=<name>; it authenticates with the key read from
# ``api_key_env``. Adding a provider = adding one entry here, no code changes.
#
# DeepSeek, Moonshot, and OpenAI expose documented OpenAI-compatible endpoints.
# MiniMax's base_url/default_model below are best-effort and MUST be verified
# against MiniMax's current API (it may use a native format); a per-environment
# override is still possible through the registry if they drift.
#
# Local-only models (GPT-OSS / Gemma) intentionally stay out of this registry.
_CLOUD_LLM_PROVIDERS: dict[str, CloudLLMProvider] = {
    "minimax": CloudLLMProvider(
        name="minimax",
        label="MiniMax",
        base_url="https://api.minimaxi.com/v1",
        default_model="MiniMax-Text-01",
        api_key_env="MINIMAX_API_KEY",
        # No verified vision model: MiniMax's /v1/chat/completions rejected the
        # guessed id and reportedly may ignore OpenAI image_url parts. Set
        # EXAMSOLVER_LLM_VISION_MODEL once a working MiniMax vision model is confirmed.
        vision_model=None,
    ),
    "deepseek": CloudLLMProvider(
        name="deepseek",
        label="DeepSeek",
        base_url="https://api.deepseek.com/v1",
        default_model="deepseek-chat",
        api_key_env="DEEPSEEK_API_KEY",
    ),
    "moonshot": CloudLLMProvider(
        name="moonshot",
        label="Moonshot Kimi",
        base_url="https://api.moonshot.cn/v1",
        default_model="moonshot-v1-8k",
        api_key_env="MOONSHOT_API_KEY",
    ),
    "openai": CloudLLMProvider(
        name="openai",
        label="OpenAI",
        base_url="https://api.openai.com/v1",
        default_model="gpt-4o-mini",
        api_key_env="OPENAI_API_KEY",
        vision_model="gpt-4o-mini",
    ),
}


def cloud_vision_model(provider: CloudLLMProvider) -> str | None:
    """Resolve the vision model for a provider: env override, then the registry.

    Returns ``None`` when no vision model is known/configured, which the router
    treats as "this provider cannot see" and degrades honestly rather than
    sending images to a text-only model.
    """

    override = os.environ.get("EXAMSOLVER_LLM_VISION_MODEL", "").strip()
    return override or provider.vision_model


def cloud_llm_provider(name: str) -> CloudLLMProvider | None:
    """Return the registered cloud provider for ``name`` (case-insensitive)."""

    return _CLOUD_LLM_PROVIDERS.get(name.strip().lower())


def cloud_llm_providers() -> tuple[CloudLLMProvider, ...]:
    """Return all registered cloud providers, for settings/UI enumeration."""

    return tuple(_CLOUD_LLM_PROVIDERS.values())
