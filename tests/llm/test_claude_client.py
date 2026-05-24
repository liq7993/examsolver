import base64
import json
import os

import httpx
import pytest
import respx

from examsolver.llm import ClaudeClient, Message, pick_llm
from examsolver.llm.claude_client import ANTHROPIC_MESSAGES_URL, STRUCTURED_OUTPUT_TOOL


def test_claude_client_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        ClaudeClient()


@respx.mock
def test_chat_posts_messages_and_returns_text(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    route = respx.post(ANTHROPIC_MESSAGES_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "content": [{"type": "text", "text": "pong"}],
                "usage": {"input_tokens": 7, "output_tokens": 3},
            },
        )
    )
    client = ClaudeClient(task_kind="explain")

    result = client.chat(
        [
            Message(role="system", content="be concise"),
            Message(role="user", content="ping"),
        ]
    )

    assert result == "pong"
    assert route.called
    request = route.calls.last.request
    assert request.headers["x-api-key"] == "test-key"
    assert request.headers["anthropic-version"] == "2023-06-01"
    payload = json.loads(request.content)
    assert payload["model"] == "claude-sonnet-4-20250514"
    assert payload["system"] == "be concise"
    assert payload["messages"] == [{"role": "user", "content": "ping"}]


@respx.mock
def test_chat_uses_tool_choice_for_json_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    schema = {
        "type": "object",
        "properties": {"answer": {"type": "string"}},
        "required": ["answer"],
    }
    route = respx.post(ANTHROPIC_MESSAGES_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "content": [
                    {
                        "type": "tool_use",
                        "id": "toolu_1",
                        "name": STRUCTURED_OUTPUT_TOOL,
                        "input": {"answer": "42"},
                    }
                ],
                "usage": {"input_tokens": 10, "output_tokens": 5},
            },
        )
    )
    client = ClaudeClient(task_kind="synthesize")

    result = client.chat([Message(role="user", content="answer")], json_schema=schema)

    assert json.loads(result) == {"answer": "42"}
    payload = json.loads(route.calls.last.request.content)
    assert payload["tools"] == [
        {
            "name": STRUCTURED_OUTPUT_TOOL,
            "description": "Return the response exactly in this structured shape.",
            "input_schema": schema,
            "strict": True,
        }
    ]
    assert payload["tool_choice"] == {"type": "tool", "name": STRUCTURED_OUTPUT_TOOL}


@respx.mock
def test_chat_retries_once_for_5xx(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    route = respx.post(ANTHROPIC_MESSAGES_URL).mock(
        side_effect=[
            httpx.Response(503, json={"error": {"message": "busy"}}),
            httpx.Response(
                200,
                json={
                    "content": [{"type": "text", "text": "recovered"}],
                    "usage": {"input_tokens": 2, "output_tokens": 1},
                },
            ),
        ]
    )
    client = ClaudeClient(task_kind="explain")

    assert client.chat([Message(role="user", content="ping")]) == "recovered"
    assert route.call_count == 2


@respx.mock
def test_chat_does_not_retry_4xx(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    route = respx.post(ANTHROPIC_MESSAGES_URL).mock(
        return_value=httpx.Response(400, json={"error": {"message": "bad request"}})
    )
    client = ClaudeClient(task_kind="explain")

    with pytest.raises(httpx.HTTPStatusError):
        client.chat([Message(role="user", content="ping")])

    assert route.call_count == 1


@respx.mock
def test_chat_with_image_sends_png_base64(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    route = respx.post(ANTHROPIC_MESSAGES_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "content": [{"type": "text", "text": "image seen"}],
                "usage": {"input_tokens": 20, "output_tokens": 2},
            },
        )
    )
    image = b"\x89PNG\r\n"
    client = ClaudeClient(task_kind="vision")

    result = client.chat_with_image([Message(role="user", content="describe")], [image])

    assert result == "image seen"
    payload = json.loads(route.calls.last.request.content)
    content = payload["messages"][0]["content"]
    assert content[0] == {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": "image/png",
            "data": base64.b64encode(image).decode("ascii"),
        },
    }
    assert content[1] == {"type": "text", "text": "describe"}


def test_router_returns_claude_for_cloud_tasks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    assert isinstance(pick_llm("synthesize", needs_vision=False), ClaudeClient)
    assert isinstance(pick_llm("explain", needs_vision=False), ClaudeClient)
    assert isinstance(pick_llm("route", needs_vision=True), ClaudeClient)
    assert pick_llm("route", needs_vision=False) is None


@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY") or not os.getenv("EXAMSOLVER_RUN_LIVE_CLAUDE"),
    reason="live Claude smoke is opt-in",
)
def test_live_claude_smoke() -> None:
    client = ClaudeClient(task_kind="explain")

    response = client.chat([Message(role="user", content="Reply with OK only.")], max_tokens=8)

    assert response
