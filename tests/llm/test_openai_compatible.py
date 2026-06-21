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


@respx.mock
def test_chat_degrades_when_provider_rejects_response_format() -> None:
    # MiniMax-style: a ``response_format: json_schema`` request is rejected with
    # 400, so the client retries once without the schema and succeeds on the
    # prompt alone instead of failing the whole solve.
    route = respx.post(CHAT_URL).mock(
        side_effect=[
            httpx.Response(400, json={"error": {"message": "response_format unsupported"}}),
            _ok_response(),
        ]
    )
    client = OpenAICompatibleClient(base_url=BASE_URL, model="cloud-model", api_key="sk")
    schema = {"type": "object", "properties": {"answer": {"type": "string"}}}

    result = client.chat([Message(role="user", content="ping")], json_schema=schema, timeout=1.0)

    assert result == "pong"
    assert route.call_count == 2
    assert "response_format" in json.loads(route.calls[0].request.content)
    assert "response_format" not in json.loads(route.calls[1].request.content)


@respx.mock
def test_chat_does_not_retry_on_non_400_status() -> None:
    # A 4xx that is not 400 (e.g. 401 auth) must surface, not silently degrade.
    route = respx.post(CHAT_URL).mock(return_value=httpx.Response(401, json={"error": "nope"}))
    client = OpenAICompatibleClient(base_url=BASE_URL, model="cloud-model", api_key="sk")
    schema = {"type": "object", "properties": {"answer": {"type": "string"}}}

    with pytest.raises(httpx.HTTPStatusError):
        client.chat([Message(role="user", content="ping")], json_schema=schema, timeout=1.0)
    assert route.call_count == 1


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
