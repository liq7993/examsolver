"""Runtime-editable LLM settings, persisted outside version control.

The settings page lets a user pick an LLM provider and paste an API key. We
persist that choice to a gitignored JSON file under ``data/`` and project it
into ``os.environ`` -- which every LLM consumer (router, Claude client,
``load_llm_config``) already reads -- so changes take effect live without a
restart and survive the next start.

Security: the key is stored server-side only, written with owner-only file
permissions where the OS supports it, and never logged. Only a masked form
(the last four characters) is ever returned to the client.
"""

from __future__ import annotations

import json
import os
import stat
from dataclasses import dataclass, field
from pathlib import Path

from examsolver.config import cloud_llm_providers

CLAUDE_PROVIDER = "claude"
LOCAL_PROVIDER = "local_gguf"
PROVIDER_ENV = "EXAMSOLVER_LLM_PROVIDER"
_CLAUDE_API_KEY_ENV = "ANTHROPIC_API_KEY"


@dataclass(frozen=True, slots=True)
class ProviderChoice:
    """A selectable LLM provider for the settings UI."""

    name: str
    label: str
    requires_key: bool
    api_key_env: str | None


@dataclass(frozen=True, slots=True)
class RuntimeSettings:
    """User-chosen provider plus API keys, keyed by provider name."""

    provider: str = ""
    api_keys: dict[str, str] = field(default_factory=dict)


def settings_path() -> Path:
    """Return the gitignored settings file path, overridable for tests."""

    configured = os.environ.get("EXAMSOLVER_SETTINGS_PATH")
    if configured:
        return Path(configured)
    return Path("data") / "runtime_settings.json"


def provider_choices() -> tuple[ProviderChoice, ...]:
    """Return every selectable provider: Claude, cloud providers, then local."""

    choices = [
        ProviderChoice(CLAUDE_PROVIDER, "Claude (Anthropic)", True, _CLAUDE_API_KEY_ENV),
    ]
    choices.extend(
        ProviderChoice(spec.name, spec.label, True, spec.api_key_env)
        for spec in cloud_llm_providers()
    )
    choices.append(ProviderChoice(LOCAL_PROVIDER, "本地 GGUF（无需 API key）", False, None))
    return tuple(choices)


def _choice_map() -> dict[str, ProviderChoice]:
    return {choice.name: choice for choice in provider_choices()}


def load_settings() -> RuntimeSettings:
    """Read settings from disk, tolerating a missing or corrupt file."""

    try:
        raw = json.loads(settings_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return RuntimeSettings()
    if not isinstance(raw, dict):
        return RuntimeSettings()

    provider_value = raw.get("provider", "")
    provider = provider_value if isinstance(provider_value, str) else ""
    api_keys_value = raw.get("api_keys", {})
    api_keys: dict[str, str] = {}
    if isinstance(api_keys_value, dict):
        for name, value in api_keys_value.items():
            if isinstance(name, str) and isinstance(value, str) and value:
                api_keys[name] = value
    return RuntimeSettings(provider=provider, api_keys=api_keys)


def save_settings(settings: RuntimeSettings) -> None:
    """Persist settings to the gitignored file with owner-only permissions."""

    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        {"provider": settings.provider, "api_keys": settings.api_keys},
        ensure_ascii=False,
        indent=2,
    )
    path.write_text(payload, encoding="utf-8")
    _restrict_permissions(path)


def _restrict_permissions(path: Path) -> None:
    try:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        # Best effort: some filesystems (e.g. Windows mounts) reject chmod.
        pass


def apply_to_environ(settings: RuntimeSettings, *, override: bool) -> None:
    """Project settings into ``os.environ`` for the LLM layer to read.

    ``override=False`` (startup) leaves any externally-set env var intact, so a
    deployment/shell-provided value wins over the stored file. ``override=True``
    (after a UI save) forces the new choice to take effect immediately.
    """

    choices = _choice_map()
    for name, key in settings.api_keys.items():
        choice = choices.get(name)
        if choice is not None and choice.api_key_env and key:
            _set_env(choice.api_key_env, key, override=override)
    if settings.provider:
        _set_env(PROVIDER_ENV, settings.provider, override=override)


def _set_env(name: str, value: str, *, override: bool) -> None:
    if override or name not in os.environ:
        os.environ[name] = value


def update_settings(*, provider: str, api_key: str | None) -> RuntimeSettings:
    """Validate, persist, and live-apply a provider/key change.

    A blank or omitted ``api_key`` keeps any previously stored key, so the user
    can switch provider without re-pasting. Unknown providers raise ``ValueError``.
    """

    normalized = provider.strip().lower()
    if normalized not in _choice_map():
        raise ValueError(f"unknown provider: {provider}")

    api_keys = dict(load_settings().api_keys)
    if api_key and api_key.strip():
        api_keys[normalized] = api_key.strip()
    updated = RuntimeSettings(provider=normalized, api_keys=api_keys)
    save_settings(updated)
    apply_to_environ(updated, override=True)
    return updated


def mask_key(key: str) -> str:
    """Return a non-reversible hint for a key: only the last four characters."""

    return f"…{key[-4:]}" if len(key) > 4 else "…"


def describe_settings() -> dict[str, object]:
    """Build the settings snapshot for the client, with keys masked.

    ``key_set`` reflects either a stored key or one already present in the
    environment, so a shell-provided key shows as configured too. The full key
    value is never included.
    """

    settings = load_settings()
    providers: list[dict[str, object]] = []
    for choice in provider_choices():
        effective = settings.api_keys.get(choice.name, "")
        if not effective and choice.api_key_env:
            effective = os.environ.get(choice.api_key_env, "")
        providers.append(
            {
                "name": choice.name,
                "label": choice.label,
                "requires_key": choice.requires_key,
                "key_set": bool(effective) if choice.requires_key else False,
                "key_masked": mask_key(effective) if effective else None,
            }
        )
    active = settings.provider or os.environ.get(PROVIDER_ENV, "")
    return {"provider": active, "providers": providers}
