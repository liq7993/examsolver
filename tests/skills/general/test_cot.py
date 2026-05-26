import json
from pathlib import Path
from typing import Any, cast

import pytest

from examsolver.contracts import SolveRequest
from examsolver.pipeline.normalizer import normalize
from examsolver.skills.base import SkillExecutionError
from examsolver.skills.general import CotWithTextbookSkill
from examsolver.skills.general._meta import SUBJECT_META
from _helpers.fake_llm import FakeLLMClient

FIXTURE_PATH = Path(__file__).with_name("cot_regression.json")


def _cases() -> list[dict[str, Any]]:
    return cast(list[dict[str, Any]], json.loads(FIXTURE_PATH.read_text(encoding="utf-8")))


def test_general_subject_meta_matches_contract() -> None:
    assert SUBJECT_META == {
        "subject": "general",
        "display_name": "通用解题",
        "color": "#888",
        "icon": "sparkles",
        "has_textbook": False,
    }


def test_cot_with_textbook_declares_type_l_capabilities() -> None:
    skill = CotWithTextbookSkill()

    assert skill.name == "general.cot_with_textbook"
    assert skill.version == "0.1.0"
    assert skill.subject == "general"
    assert skill.question_types == ["unknown", "general"]
    assert skill.skill_type == "llm"
    assert skill.needs_vision is False
    assert skill.needs_rag is False
    assert skill.can_handle(normalize(SolveRequest(question="任意问题"))) is True


@pytest.mark.parametrize("case", _cases(), ids=lambda case: str(case["name"]))
def test_cot_with_textbook_solves_fixture_with_fake_llm(case: dict[str, Any]) -> None:
    skill = CotWithTextbookSkill()
    question = normalize(SolveRequest(question=str(case["question"])))
    llm = FakeLLMClient.from_recorded(cast(dict[str, object], case["llm_response"]))

    result = skill.solve(question, llm=llm)

    assert result.skill == "general.cot_with_textbook"
    assert result.question_type == "unknown"
    assert result.meta["success"] is True
    assert case["expected_answer_contains"] in str(result.answer)
    assert len(result.steps) == case["expected_step_count"]
    assert result.student_explanation is not None
    assert result.student_explanation.common_mistake
    assert result.meta["common_mistakes"]
    assert llm.call_count == 1
    assert llm.last_json_schema is not None


def test_cot_with_textbook_rejects_malformed_llm_response() -> None:
    skill = CotWithTextbookSkill()
    question = normalize(SolveRequest(question="解释天气"))
    llm = FakeLLMClient.always('{"thinking":"x","steps":[],"answer":"","common_mistakes":[]}')

    with pytest.raises(SkillExecutionError):
        skill.solve(question, llm=llm)
