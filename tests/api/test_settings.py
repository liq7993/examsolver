import json
import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import HTTPException

from examsolver.api.routes.settings import get_config, update_config
from examsolver.api.schemas import UpdateSettingsBody
from examsolver.runtime_settings import PROVIDER_ENV

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


def test_get_config_lists_providers_with_no_keys_set() -> None:
    body = get_config()

    names = {provider.name for provider in body.providers}
    assert {"claude", "deepseek", "openai", "local_gguf"} <= names
    assert "qwen" not in names
    assert all(not provider.key_set for provider in body.providers)


def test_update_config_sets_provider_and_returns_masked_key() -> None:
    body = update_config(UpdateSettingsBody(provider="deepseek", api_key="sk-route-4321"))

    assert body.provider == "deepseek"
    deepseek = next(provider for provider in body.providers if provider.name == "deepseek")
    assert deepseek.key_set is True
    assert deepseek.key_masked == "…4321"
    assert "sk-route-4321" not in json.dumps(body.model_dump(), ensure_ascii=False)


def test_update_config_rejects_unknown_provider() -> None:
    with pytest.raises(HTTPException) as exc_info:
        update_config(UpdateSettingsBody(provider="qwen", api_key="sk-nope"))

    assert exc_info.value.status_code == 400
