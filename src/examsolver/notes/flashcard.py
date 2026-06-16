"""Generate review flashcards from note entries."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Literal, cast

from examsolver.contracts import Flashcard, NoteEntry
from examsolver.llm.base import LLMClient, Message

CardType = Literal["formula", "concept", "trap"]
PROMPT_PATH = Path(__file__).with_name("prompts") / "flashcard_extract.zh.md"
FLASHCARD_SCHEMA: dict[str, object] = {
    "type": "object",
    "required": ["flashcards"],
    "properties": {
        "flashcards": {
            "type": "array",
            "minItems": 2,
            "items": {
                "type": "object",
                "required": ["front", "back", "card_type"],
                "properties": {
                    "front": {"type": "string"},
                    "back": {"type": "string"},
                    "card_type": {"type": "string", "enum": ["formula", "concept", "trap"]},
                },
                "additionalProperties": False,
            },
        }
    },
    "additionalProperties": False,
}


def generate_flashcards(note: NoteEntry, *, llm: LLMClient | None) -> list[Flashcard]:
    """Return flashcards for a note; parsing failures degrade to an empty list."""

    if llm is None:
        return []
    for _ in range(2):
        try:
            return _parse_flashcards(_call_llm(note, llm=llm))
        except Exception:
            continue
    return []


def _call_llm(note: NoteEntry, *, llm: LLMClient) -> dict[str, Any]:
    raw = llm.chat(
        [
            Message(role="system", content=PROMPT_PATH.read_text(encoding="utf-8")),
            Message(role="user", content=json.dumps(_note_payload(note), ensure_ascii=False)),
        ],
        json_schema=FLASHCARD_SCHEMA,
        max_tokens=800,
        temperature=0.1,
    )
    data = json.loads(_strip_code_fence(raw))
    if not isinstance(data, dict):
        raise ValueError("flashcard response must be a JSON object")
    return cast(dict[str, Any], data)


def _parse_flashcards(payload: dict[str, Any]) -> list[Flashcard]:
    raw_cards = payload.get("flashcards")
    if not isinstance(raw_cards, list) or len(raw_cards) < 2:
        raise ValueError("at least two flashcards are required")
    cards: list[Flashcard] = []
    for raw_card in raw_cards:
        if not isinstance(raw_card, dict):
            raise ValueError("flashcard must be an object")
        front = raw_card.get("front")
        back = raw_card.get("back")
        card_type = raw_card.get("card_type")
        if not isinstance(front, str) or not front.strip():
            raise ValueError("front must be a non-empty string")
        if not isinstance(back, str) or not back.strip():
            raise ValueError("back must be a non-empty string")
        if card_type not in {"formula", "concept", "trap"}:
            raise ValueError("card_type is invalid")
        cards.append(Flashcard(front=front.strip(), back=back.strip(), card_type=card_type))
    return cards


def _note_payload(note: NoteEntry) -> dict[str, Any]:
    data = asdict(note)
    data["created_at"] = note.created_at.isoformat() if note.created_at is not None else None
    return data


def _strip_code_fence(content: str) -> str:
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return text
