import json

import pytest

from examsolver.llm.base import LLMClient, Message
from _helpers.fake_llm import FakeLLMClient, prompt_hash


def test_from_recorded_returns_single_string_response() -> None:
    client: LLMClient = FakeLLMClient.from_recorded("ok")
    messages = [Message(role="user", content="anything")]

    assert client.chat(messages) == "ok"


def test_from_recorded_serializes_dict_payload() -> None:
    client = FakeLLMClient.from_recorded({"answer": "42"})

    assert json.loads(client.chat([Message(role="user", content="anything")])) == {"answer": "42"}


def test_record_matches_multiple_rules_by_substring() -> None:
    client = FakeLLMClient()
    client.record(prompt_contains="derivative", response="calculus")
    client.record(prompt_contains="matrix", response="linear algebra")

    assert client.chat([Message(role="user", content="find derivative of x^2")]) == "calculus"
    assert client.chat([Message(role="user", content="multiply this matrix")]) == "linear algebra"


def test_recorded_hash_matches_task_kind_and_prompt_hash() -> None:
    content = "classify this prompt"
    client = FakeLLMClient(task_kind="route")
    client.record_hash(prompt_hash=prompt_hash(content), response='{"type":"unknown"}')

    assert client.chat([Message(role="user", content=content)]) == '{"type":"unknown"}'


def test_unmatched_prompt_raises_assertion_error() -> None:
    client = FakeLLMClient()

    with pytest.raises(AssertionError, match="FakeLLM: unexpected prompt: unknown"):
        client.chat([Message(role="user", content="unknown")])


def test_chat_with_image_uses_chat_path() -> None:
    client = FakeLLMClient.always("seen")

    assert client.chat_with_image([Message(role="user", content="describe")], [b"image"]) == "seen"


def test_call_count_and_last_call_state_are_recorded() -> None:
    schema: dict[str, object] = {"type": "object"}
    messages = [
        Message(role="system", content="be brief"),
        Message(role="user", content="ping"),
    ]
    client = FakeLLMClient.always("pong")

    assert client.chat(messages, json_schema=schema) == "pong"
    assert client.chat(messages) == "pong"

    assert client.call_count == 2
    assert client.last_messages == messages
    assert client.last_json_schema is None
