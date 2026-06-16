from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from _helpers.fake_llm import FakeLLMClient
from examsolver.contracts import NormalizedQuestion, SolveRequest
from examsolver.pipeline.classifier import classify
from examsolver.pipeline.normalizer import normalize
from examsolver.skills import registry
from examsolver.skills.base import SkillExecutionError
from examsolver.skills.mechanism import GearTrainSkill
from examsolver.skills.mechanism._meta import SUBJECT_META

FIXTURE_PATH = Path(__file__).with_name("gear_train_regression.json")


def _cases() -> list[dict[str, Any]]:
    return cast(list[dict[str, Any]], json.loads(FIXTURE_PATH.read_text(encoding="utf-8")))


def test_mechanism_subject_meta_matches_contract() -> None:
    assert SUBJECT_META == {
        "subject": "mechanism",
        "display_name": "机械原理",
        "color": "#4a6fa5",
        "icon": "gear",
        "has_textbook": False,
    }


def test_gear_train_declares_type_h_capabilities() -> None:
    skill = GearTrainSkill()
    question = normalize(SolveRequest(question="两级齿轮传动 z1=20 z2=40，求传动比"))

    assert skill.name == "mechanism.gear_train"
    assert skill.version == "0.1.0"
    assert skill.subject == "mechanism"
    assert skill.question_types == ["gear_train"]
    assert skill.skill_type == "hybrid"
    assert skill.needs_vision is True
    assert skill.needs_rag is False
    assert skill.can_handle(question) is True
    assert question.subject == "mechanism"
    assert classify(question) == "gear_train"


@pytest.mark.parametrize("case", _cases(), ids=lambda case: str(case["id"]))
def test_gear_train_solves_fixture_with_fake_llm(case: dict[str, Any]) -> None:
    skill = GearTrainSkill()
    question = _question(
        str(case["question"]),
        ocr=str(case.get("ocr", "")),
        vision=str(case.get("vision", "")),
    )
    llm = FakeLLMClient.from_recorded(cast(dict[str, object], case["llm_response"]))

    result = skill.solve(question, llm=llm)

    assert result.skill == "mechanism.gear_train"
    assert result.question_type == "gear_train"
    assert result.meta["success"] is True
    assert result.meta["mechanism.gear_train.ratio"] == pytest.approx(
        float(case["expected_ratio"])
    )
    assert case["expected_answer_contains"] in str(result.answer)
    assert result.meta["mechanism.gear_train.stages_count"] >= 1
    assert len(result.steps) == result.meta["mechanism.gear_train.stages_count"] + 1
    assert result.student_explanation is not None
    assert llm.call_count == 1
    assert llm.last_json_schema is not None
    assert "stages" in json.dumps(llm.last_json_schema)
    assert str(case.get("vision", "无")) in (llm.last_messages or [])[-1].content


def test_gear_train_rejects_missing_llm() -> None:
    with pytest.raises(SkillExecutionError, match="requires an LLM"):
        GearTrainSkill().solve(_question("单级齿轮传动 z1=18 z2=54，求传动比"))


def test_gear_train_rejects_unclear_teeth_without_fabricating() -> None:
    question = _question("图中齿轮很模糊，求传动比", vision="图太糊，看不清齿数。")
    llm = FakeLLMClient.from_recorded({"stages": []})

    with pytest.raises(SkillExecutionError, match="could not extract"):
        GearTrainSkill().solve(question, llm=llm)


def test_gear_train_rejects_invalid_teeth() -> None:
    question = _question("齿轮传动比")
    llm = FakeLLMClient.from_recorded({"stages": [{"driving_teeth": 0, "driven_teeth": 40}]})

    with pytest.raises(SkillExecutionError):
        GearTrainSkill().solve(question, llm=llm)


def test_registry_discovers_mechanism_gear_train() -> None:
    registry._reset_for_tests()

    skill = registry.get_skill("mechanism", "gear_train")

    assert skill is not None
    assert skill.name == "mechanism.gear_train"


def _question(text: str, *, ocr: str = "", vision: str = "") -> NormalizedQuestion:
    normalized = normalize(SolveRequest(question=text))
    return NormalizedQuestion(
        raw_text=normalized.raw_text,
        normalized_text=normalized.normalized_text,
        subject=normalized.subject,
        has_image=bool(ocr or vision),
        image_paths=["diagram.png"] if ocr or vision else [],
        ocr_text=ocr,
        vision_description=vision,
        hints=normalized.hints,
    )
