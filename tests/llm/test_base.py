from typing import Any

from examsolver.llm import LLMClient, Message, pick_llm


class FakeClient:
    def chat(
        self,
        messages: list[Message],
        *,
        json_schema: dict[str, object] | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
        timeout: float = 30.0,
    ) -> str:
        assert messages
        assert json_schema is None or isinstance(json_schema, dict)
        assert max_tokens > 0
        assert temperature >= 0
        assert timeout > 0
        return messages[-1].content

    def chat_with_image(
        self,
        messages: list[Message],
        images: list[bytes],
        **kwargs: Any,
    ) -> str:
        assert messages
        assert images
        assert kwargs == {} or isinstance(kwargs, dict)
        return messages[-1].content


def test_message_defaults_to_empty_image_list() -> None:
    first = Message(role="user", content="hello")
    second = Message(role="assistant", content="world")

    assert first.role == "user"
    assert first.content == "hello"
    assert first.images == []
    assert first.images is not second.images


def test_llm_client_protocol_shape_accepts_fake_client() -> None:
    client: LLMClient = FakeClient()
    messages = [Message(role="user", content="ping")]

    assert client.chat(messages) == "ping"
    assert client.chat(messages, json_schema={"type": "object"}, timeout=1.0) == "ping"
    assert client.chat_with_image(messages, [b"image"]) == "ping"


def test_pick_llm_returns_none_until_clients_are_registered() -> None:
    assert pick_llm("general_solve", needs_vision=False) is None
