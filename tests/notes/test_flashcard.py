from __future__ import annotations

import json

from _helpers.fake_llm import FakeLLMClient
from examsolver.contracts import NormalizedQuestion, NoteEntry, SolveResult, Step
from examsolver.notes.flashcard import generate_flashcards
from examsolver.notes.note_builder import build_note


def test_generate_flashcards_from_note_with_fake_llm() -> None:
    note = _note()
    llm = FakeLLMClient.from_recorded(
        {
            "flashcards": [
                {
                    "front": "幂函数求导法则是什么？",
                    "back": "$(x^n)'=nx^{n-1}$",
                    "card_type": "formula",
                },
                {
                    "front": "求导时常见陷阱是什么？",
                    "back": "不要漏乘指数，也不要把原函数当作导数。",
                    "card_type": "trap",
                },
            ]
        }
    )

    cards = generate_flashcards(note, llm=llm)

    assert len(cards) == 2
    assert cards[0].card_type == "formula"
    assert cards[0].tag == "formula"
    assert cards[1].card_type == "trap"
    assert llm.call_count == 1
    assert llm.last_json_schema is not None
    assert "flashcards" in json.dumps(llm.last_json_schema)


def test_generate_flashcards_retries_once_after_malformed_json() -> None:
    note = _note()
    llm = _SequenceLLM(
        [
            "not json",
            json.dumps(
            {
                "flashcards": [
                    {"front": "公式？", "back": "答案", "card_type": "formula"},
                    {"front": "概念？", "back": "答案", "card_type": "concept"},
                ]
            },
            ensure_ascii=False,
            ),
        ]
    )

    cards = generate_flashcards(note, llm=llm)

    assert len(cards) == 2
    assert llm.call_count == 2


def test_generate_flashcards_degrades_to_empty_after_repeated_failures() -> None:
    llm = FakeLLMClient.always("not json")

    assert generate_flashcards(_note(), llm=llm) == []
    assert llm.call_count == 2


def test_generate_flashcards_degrades_to_empty_without_llm() -> None:
    assert generate_flashcards(_note(), llm=None) == []


def _note() -> NoteEntry:
    question = NormalizedQuestion(
        raw_text="求导",
        normalized_text="求 x^2 对 x 的导数",
        subject="calculus",
        hints={"solve_id": "solve-1"},
    )
    result = SolveResult(
        question_type="derivative",
        skill="calculus.derivative",
        steps=[Step(index=1, description="识别幂函数", formula_latex="x^2")],
        answer="$2x$",
        meta={
            "success": True,
            "common_mistakes": ["不要漏乘指数。"],
        },
    )
    return build_note(result, question)


class _SequenceLLM:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.call_count = 0

    def chat(self, *args: object, **kwargs: object) -> str:
        _ = (args, kwargs)
        response = self.responses[self.call_count]
        self.call_count += 1
        return response

    def chat_with_image(self, *args: object, **kwargs: object) -> str:
        return self.chat(*args, **kwargs)
