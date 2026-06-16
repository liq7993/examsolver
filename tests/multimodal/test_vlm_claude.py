import base64
import json

import httpx
import pytest
import respx

from examsolver.llm.claude_client import ANTHROPIC_MESSAGES_URL
from examsolver.multimodal import VLMError
from examsolver.multimodal.vlm_claude import ClaudeVLMClient


def test_claude_vlm_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(VLMError, match="ANTHROPIC_API_KEY"):
        ClaudeVLMClient()


def test_describe_requires_at_least_one_image(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    client = ClaudeVLMClient()

    with pytest.raises(VLMError, match="at least one image"):
        client.describe([], "描述图中机构")


@respx.mock
def test_describe_posts_images_and_returns_visible_description(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    route = respx.post(ANTHROPIC_MESSAGES_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "content": [{"type": "text", "text": "两级齿轮传动，z1=20，z2=40。"}],
                "usage": {"input_tokens": 30, "output_tokens": 12},
            },
        )
    )
    image = b"\x89PNG\r\n"

    result = ClaudeVLMClient().describe([image], "描述图中机构的齿轮与齿数")

    assert result == "两级齿轮传动，z1=20，z2=40。"
    payload = json.loads(route.calls.last.request.content)
    assert payload["model"] == "claude-sonnet-4-20250514"
    assert "不要解题" in payload["system"]
    assert payload["messages"][0]["role"] == "user"
    content = payload["messages"][0]["content"]
    assert content[0] == {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": "image/png",
            "data": base64.b64encode(image).decode("ascii"),
        },
    }
    assert content[1] == {"type": "text", "text": "描述图中机构的齿轮与齿数"}


@respx.mock
def test_describe_retries_once_for_transient_cloud_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    route = respx.post(ANTHROPIC_MESSAGES_URL).mock(
        side_effect=[
            httpx.Response(503, json={"error": {"message": "busy"}}),
            httpx.Response(
                200,
                json={
                    "content": [{"type": "text", "text": "恢复后看到齿轮标注。"}],
                    "usage": {"input_tokens": 10, "output_tokens": 5},
                },
            ),
        ]
    )

    result = ClaudeVLMClient().describe([b"\x89PNG\r\n"], "描述图中机构")

    assert result == "恢复后看到齿轮标注。"
    assert route.call_count == 2


@respx.mock
def test_describe_raises_when_claude_returns_empty_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    respx.post(ANTHROPIC_MESSAGES_URL).mock(
        return_value=httpx.Response(
            200,
            json={"content": [{"type": "text", "text": "   "}]},
        )
    )

    with pytest.raises(VLMError, match="empty description"):
        ClaudeVLMClient().describe([b"\x89PNG\r\n"], "描述图中机构")


@respx.mock
def test_describe_raises_after_cloud_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    route = respx.post(ANTHROPIC_MESSAGES_URL).mock(
        side_effect=[
            httpx.Response(503, json={"error": {"message": "busy"}}),
            httpx.Response(503, json={"error": {"message": "still busy"}}),
        ]
    )

    with pytest.raises(VLMError, match="description failed"):
        ClaudeVLMClient().describe([b"\x89PNG\r\n"], "描述图中机构")

    assert route.call_count == 2
