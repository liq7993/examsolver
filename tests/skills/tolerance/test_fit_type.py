from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from _helpers.fake_llm import FakeLLMClient
from examsolver.contracts import SolveRequest
from examsolver.pipeline.classifier import classify
from examsolver.pipeline.normalizer import normalize
from examsolver.rag.retriever import TextbookChunk
from examsolver.skills import registry
from examsolver.skills.base import SkillExecutionError
from examsolver.skills.tolerance import FitTypeSkill
from examsolver.skills.tolerance._meta import SUBJECT_META
from examsolver.skills.tolerance._tables import judge_fit_type, lookup_basic_deviation

FIXTURE_PATH = Path(__file__).with_name("fit_type_regression.json")


def _cases() -> list[dict[str, Any]]:
    return cast(list[dict[str, Any]], json.loads(FIXTURE_PATH.read_text(encoding="utf-8")))


def _fake_chunks(query: str, subject: str, top_k: int = 5) -> list[TextbookChunk]:
    assert subject == "tolerance"
    assert top_k == 3
    return [
        TextbookChunk(
            id="chunk-h7",
            document_id="doc-tolerance",
            document_title="公差与测量",
            subject="tolerance",
            page=12,
            text=f"教材片段：{query} 中 H7/g6 常用于说明孔轴配合。",
            score=0.1,
        )
    ]


def test_tolerance_subject_meta_matches_contract() -> None:
    assert SUBJECT_META == {
        "subject": "tolerance",
        "display_name": "公差与测量",
        "color": "#2f6f73",
        "icon": "ruler",
        "has_textbook": True,
    }


def test_lookup_basic_deviation_supports_common_symbols() -> None:
    symbols = [
        ("H7", "hole"),
        ("h6", "shaft"),
        ("g6", "shaft"),
        ("G7", "hole"),
        ("k6", "shaft"),
        ("K7", "hole"),
    ]

    deviations = [lookup_basic_deviation(symbol, component) for symbol, component in symbols]

    assert [deviation.symbol for deviation in deviations] == ["H7", "h6", "g6", "G7", "k6", "K7"]
    assert judge_fit_type(lookup_basic_deviation("H7", "hole"), lookup_basic_deviation("g6", "shaft")) == "间隙"
    assert judge_fit_type(lookup_basic_deviation("H7", "hole"), lookup_basic_deviation("k6", "shaft")) == "过渡"


def test_fit_type_declares_type_h_capabilities() -> None:
    skill = FitTypeSkill()
    question = normalize(SolveRequest(question="H7/g6 是什么配合？"))

    assert skill.name == "tolerance.fit_type"
    assert skill.version == "0.1.0"
    assert skill.subject == "tolerance"
    assert skill.question_types == ["fit_type"]
    assert skill.skill_type == "hybrid"
    assert skill.needs_vision is False
    assert skill.needs_rag is True
    assert skill.can_handle(question) is True
    assert question.subject == "tolerance"
    assert classify(question) == "fit_type"
    assert classify(normalize(SolveRequest(question="H7/g6"))) == "fit_type"
    assert classify(normalize(SolveRequest(question="请说明孔的基本偏差代号 H 和轴的 h 区别"))) == "fit_type"


@pytest.mark.parametrize("case", _cases(), ids=lambda case: str(case["name"]))
def test_fit_type_solves_fixture_with_fake_llm(case: dict[str, Any]) -> None:
    skill = FitTypeSkill()
    question = normalize(SolveRequest(question=str(case["question"])))
    llm = FakeLLMClient.from_recorded(cast(dict[str, object], case["llm_response"]))

    result = skill.solve(question, llm=llm, rag_retrieve=_fake_chunks)

    assert result.skill == "tolerance.fit_type"
    assert result.question_type == "fit_type"
    assert result.meta["success"] is True
    assert result.meta["tolerance.fit_type.fit_type"] == case["expected_fit_type"]
    assert case["expected_answer_contains"] in str(result.answer)
    assert len(result.steps) == 4
    assert result.student_explanation is not None
    assert result.citations
    assert result.citations[0].source == "公差与测量"
    assert result.citations[0].chunk_id == "chunk-h7"
    assert llm.call_count == 1
    assert llm.last_json_schema is not None
    assert "hole_symbol" in json.dumps(llm.last_json_schema)


def test_fit_type_regex_fallback_supports_smoke_without_llm() -> None:
    question = normalize(SolveRequest(question="H7/g6 是什么配合？"))

    result = FitTypeSkill().solve(question, rag_retrieve=_fake_chunks)

    assert result.answer == "H7/g6 属于间隙配合"
    assert result.citations


def test_fit_type_regex_fallback_supports_bare_h_and_h() -> None:
    question = normalize(SolveRequest(question="请说明孔的基本偏差代号 H 和轴的 h 区别"))

    result = FitTypeSkill().solve(question, rag_retrieve=_fake_chunks)

    assert result.answer == "H/h 属于间隙配合"
    assert result.meta["tolerance.fit_type.hole_symbol"] == "H"
    assert result.meta["tolerance.fit_type.shaft_symbol"] == "h"
    assert result.citations


def test_fit_type_rejects_malformed_llm_response() -> None:
    question = normalize(SolveRequest(question="H7/g6 是什么配合？"))
    llm = FakeLLMClient.always('{"hole_symbol":"","shaft_symbol":"g6"}')

    with pytest.raises(SkillExecutionError):
        FitTypeSkill().solve(question, llm=llm, rag_retrieve=_fake_chunks)


def test_registry_discovers_tolerance_fit_type() -> None:
    registry._reset_for_tests()

    skill = registry.get_skill("tolerance", "fit_type")

    assert skill is not None
    assert skill.name == "tolerance.fit_type"
