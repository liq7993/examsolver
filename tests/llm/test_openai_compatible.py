import json

import httpx
import pytest
import respx

from examsolver.config import cloud_llm_provider, cloud_llm_providers
from examsolver.llm import (
    ClaudeClient,
    LocalGGUFClient,
    Message,
    OpenAICompatibleClient,
    pick_llm,
)

BASE_URL = "http://cloud.test/v1"
CHAT_URL = f"{BASE_URL}/chat/completions"


def _ok_response() -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "choices": [{"message": {"content": "pong"}}],
            "usage": {"prompt_tokens": 4, "completion_tokens": 2},
        },
    )


@respx.mock
def test_cloud_client_sends_bearer_auth_header() -> None:
    route = respx.post(CHAT_URL).mock(return_value=_ok_response())
    client = OpenAICompatibleClient(
        base_url=BASE_URL,
        model="cloud-model",
        api_key="sk-secret",
        provider_label="deepseek",
    )

    result = client.chat([Message(role="user", content="ping")], timeout=1.0)

    assert result == "pong"
    request = route.calls.last.request
    assert request.headers["authorization"] == "Bearer sk-secret"
    assert json.loads(request.content) == {
        "model": "cloud-model",
        "messages": [{"role": "user", "content": "ping"}],
        "temperature": 0.2,
        "max_tokens": 1024,
        "stream": False,
    }


@respx.mock
def test_client_without_key_sends_no_auth_header() -> None:
    route = respx.post(CHAT_URL).mock(return_value=_ok_response())
    client = OpenAICompatibleClient(base_url=BASE_URL, model="cloud-model")

    assert client.chat([Message(role="user", content="ping")]) == "pong"
    assert "authorization" not in route.calls.last.request.headers


def test_local_gguf_is_an_openai_compatible_client_without_key() -> None:
    client = LocalGGUFClient(base_url=BASE_URL, model="local-model")

    assert isinstance(client, OpenAICompatibleClient)
    assert client._api_key is None


def test_registry_exposes_known_providers() -> None:
    names = {provider.name for provider in cloud_llm_providers()}

    assert {"deepseek", "openai"} <= names
    assert cloud_llm_provider("DeepSeek") is cloud_llm_provider("deepseek")
    assert cloud_llm_provider("deepseek") is not None
    assert cloud_llm_provider("nope") is None


def test_router_selects_cloud_client_for_keyed_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EXAMSOLVER_LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")

    for task_kind in ("route", "extract_simple", "synthesize", "explain", "general_solve"):
        client = pick_llm(task_kind, needs_vision=False)
        assert isinstance(client, OpenAICompatibleClient)
        assert not isinstance(client, LocalGGUFClient)


def test_router_keeps_vision_on_claude_even_with_cloud_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EXAMSOLVER_LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    client = pick_llm("extract_simple", needs_vision=True)

    assert isinstance(client, ClaudeClient)


def test_router_falls_back_when_cloud_provider_has_no_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EXAMSOLVER_LLM_PROVIDER", "minimax")
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)

    client = pick_llm("route", needs_vision=False)

    assert isinstance(client, LocalGGUFClient)
