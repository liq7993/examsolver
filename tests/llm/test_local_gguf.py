import json
import os

import httpx
import pytest
import respx

from examsolver.llm import LocalGGUFClient, Message, pick_llm

BASE_URL = "http://llama.test/v1"
CHAT_URL = f"{BASE_URL}/chat/completions"


@respx.mock
def test_local_gguf_chat_posts_openai_compatible_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EXAMSOLVER_LLM_BASE_URL", BASE_URL)
    monkeypatch.setenv("EXAMSOLVER_LLM_MODEL", "local-model")
    route = respx.post(CHAT_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "pong"}}],
                "usage": {"prompt_tokens": 4, "completion_tokens": 2},
            },
        )
    )
    client = LocalGGUFClient(task_kind="route")

    result = client.chat([Message(role="user", content="ping")], timeout=1.0)

    assert result == "pong"
    payload = json.loads(route.calls.last.request.content)
    assert payload == {
        "model": "local-model",
        "messages": [{"role": "user", "content": "ping"}],
        "temperature": 0.2,
        "max_tokens": 1024,
        "stream": False,
    }


@respx.mock
def test_local_gguf_chat_adds_json_schema_response_format(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EXAMSOLVER_LLM_BASE_URL", BASE_URL)
    monkeypatch.setenv("EXAMSOLVER_LLM_MODEL", "local-model")
    schema: dict[str, object] = {
        "type": "object",
        "properties": {"answer": {"type": "string"}},
        "required": ["answer"],
    }
    route = respx.post(CHAT_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "{\"answer\":\"42\"}"}}],
                "usage": {"prompt_tokens": 8, "completion_tokens": 4},
            },
        )
    )
    client = LocalGGUFClient(task_kind="extract_simple")

    result = client.chat([Message(role="user", content="answer")], json_schema=schema)

    assert json.loads(result) == {"answer": "42"}
    payload = json.loads(route.calls.last.request.content)
    assert payload["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "structured_output",
            "schema": schema,
            "strict": True,
        },
    }


@respx.mock
def test_local_gguf_retries_once_for_5xx(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXAMSOLVER_LLM_BASE_URL", BASE_URL)
    route = respx.post(CHAT_URL).mock(
        side_effect=[
            httpx.Response(502, json={"error": "busy"}),
            httpx.Response(
                200,
                json={
                    "choices": [{"message": {"content": "recovered"}}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1},
                },
            ),
        ]
    )
    client = LocalGGUFClient(model="local-model", task_kind="route")

    assert client.chat([Message(role="user", content="ping")]) == "recovered"
    assert route.call_count == 2


@respx.mock
def test_local_gguf_does_not_retry_4xx(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXAMSOLVER_LLM_BASE_URL", BASE_URL)
    route = respx.post(CHAT_URL).mock(return_value=httpx.Response(400, json={"error": "bad"}))
    client = LocalGGUFClient(model="local-model", task_kind="route")

    with pytest.raises(httpx.HTTPStatusError):
        client.chat([Message(role="user", content="ping")])

    assert route.call_count == 1


def test_local_gguf_chat_with_image_is_not_supported() -> None:
    client = LocalGGUFClient(base_url=BASE_URL, model="local-model")

    with pytest.raises(NotImplementedError):
        client.chat_with_image([Message(role="user", content="describe")], [b"image"])


def test_router_returns_local_gguf_for_cheap_text_tasks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("EXAMSOLVER_LLM_PROVIDER", raising=False)
    monkeypatch.setenv("EXAMSOLVER_LLM_BASE_URL", BASE_URL)
    monkeypatch.setenv("EXAMSOLVER_LLM_MODEL", "local-model")

    assert isinstance(pick_llm("route", needs_vision=False), LocalGGUFClient)
    assert isinstance(pick_llm("extract_simple", needs_vision=False), LocalGGUFClient)
    assert pick_llm("unknown_task", needs_vision=False) is None


@pytest.mark.local
@pytest.mark.skipif(
    not os.getenv("EXAMSOLVER_RUN_LOCAL_GGUF"),
    reason="local llama-server smoke is opt-in",
)
def test_local_gguf_live_smoke() -> None:
    client = LocalGGUFClient(task_kind="route")

    response = client.chat([Message(role="user", content="Reply with OK only.")], max_tokens=8)

    assert response
