import json
import os
from collections.abc import Iterator
from pathlib import Path
from typing import cast

import pytest

from examsolver.runtime_settings import (
    PROVIDER_ENV,
    RuntimeSettings,
    apply_to_environ,
    describe_settings,
    load_settings,
    mask_key,
    provider_choices,
    save_settings,
    settings_path,
    update_settings,
)

# Every env var the settings layer may touch, so each test starts clean and
# nothing leaks between tests (the code writes os.environ directly, not via
# monkeypatch, so we snapshot and fully restore).
_TOUCHED_ENV = (
    PROVIDER_ENV,
    "ANTHROPIC_API_KEY",
    "MINIMAX_API_KEY",
    "DEEPSEEK_API_KEY",
    "MOONSHOT_API_KEY",
    "OPENAI_API_KEY",
)


@pytest.fixture(autouse=True)
def _isolate_env_and_settings(tmp_path: Path) -> Iterator[None]:
    saved = dict(os.environ)
    for var in _TOUCHED_ENV:
        os.environ.pop(var, None)
    os.environ["EXAMSOLVER_SETTINGS_PATH"] = str(tmp_path / "runtime_settings.json")
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(saved)


def test_mask_key_reveals_only_last_four() -> None:
    assert mask_key("sk-secret-abcd") == "…abcd"
    assert mask_key("tiny") == "…"
    assert mask_key("") == "…"


def test_save_and_load_round_trip() -> None:
    settings = RuntimeSettings(provider="deepseek", api_keys={"deepseek": "sk-1234"})

    save_settings(settings)
    loaded = load_settings()

    assert loaded.provider == "deepseek"
    assert loaded.api_keys == {"deepseek": "sk-1234"}


def test_load_settings_tolerates_missing_file() -> None:
    assert not settings_path().exists()

    loaded = load_settings()

    assert loaded == RuntimeSettings()


def test_update_settings_persists_and_applies_to_environ() -> None:
    update_settings(provider="deepseek", api_key="sk-live-5678")

    reloaded = load_settings()
    assert reloaded.provider == "deepseek"
    assert reloaded.api_keys["deepseek"] == "sk-live-5678"
    assert os.environ["DEEPSEEK_API_KEY"] == "sk-live-5678"
    assert os.environ[PROVIDER_ENV] == "deepseek"


def test_update_settings_keeps_existing_key_when_blank() -> None:
    update_settings(provider="deepseek", api_key="sk-keep-9012")

    update_settings(provider="deepseek", api_key="   ")

    assert load_settings().api_keys["deepseek"] == "sk-keep-9012"


def test_update_settings_normalizes_provider_case() -> None:
    settings = update_settings(provider="DeepSeek", api_key="sk-norm-3456")

    assert settings.provider == "deepseek"


def test_update_settings_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError, match="qwen"):
        update_settings(provider="qwen", api_key="sk-nope")


def test_apply_to_environ_startup_does_not_override_shell_env() -> None:
    os.environ["DEEPSEEK_API_KEY"] = "shell-provided"

    apply_to_environ(
        RuntimeSettings(provider="deepseek", api_keys={"deepseek": "file-key"}),
        override=False,
    )

    assert os.environ["DEEPSEEK_API_KEY"] == "shell-provided"
    assert os.environ[PROVIDER_ENV] == "deepseek"


def test_apply_to_environ_override_replaces_shell_env() -> None:
    os.environ["DEEPSEEK_API_KEY"] = "shell-provided"

    apply_to_environ(
        RuntimeSettings(provider="deepseek", api_keys={"deepseek": "file-key"}),
        override=True,
    )

    assert os.environ["DEEPSEEK_API_KEY"] == "file-key"


def test_provider_choices_excludes_qwen_and_marks_local_keyless() -> None:
    choices = {choice.name: choice for choice in provider_choices()}

    assert {"claude", "deepseek", "openai", "local_gguf"} <= set(choices)
    assert "qwen" not in choices
    assert choices["claude"].requires_key is True
    assert choices["local_gguf"].requires_key is False
    assert choices["local_gguf"].api_key_env is None


def test_describe_settings_masks_keys_and_never_returns_full() -> None:
    update_settings(provider="deepseek", api_key="sk-secret-7890")

    snapshot = describe_settings()

    assert snapshot["provider"] == "deepseek"
    providers = cast(list[dict[str, object]], snapshot["providers"])
    deepseek = next(p for p in providers if p["name"] == "deepseek")
    assert deepseek["key_set"] is True
    assert deepseek["key_masked"] == "…7890"
    assert "sk-secret-7890" not in json.dumps(snapshot, ensure_ascii=False)


def test_describe_settings_treats_env_provided_key_as_set() -> None:
    os.environ["OPENAI_API_KEY"] = "sk-env-only-2222"

    snapshot = describe_settings()

    providers = cast(list[dict[str, object]], snapshot["providers"])
    openai = next(p for p in providers if p["name"] == "openai")
    assert openai["key_set"] is True
    assert openai["key_masked"] == "…2222"
