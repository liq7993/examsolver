import json
from pathlib import Path
from typing import Any, cast

import pytest

from examsolver.contracts import SolveRequest, Step
from examsolver.pipeline.classifier import classify
from examsolver.pipeline.normalizer import normalize
from examsolver.skills.mechanics import ForceBalanceSkill


FIXTURE_PATH = Path(__file__).parents[2] / "fixtures" / "force_balance_regression.json"


def _cases() -> list[dict[str, Any]]:
    return cast(list[dict[str, Any]], json.loads(FIXTURE_PATH.read_text(encoding="utf-8")))


@pytest.mark.parametrize("case", _cases(), ids=lambda case: str(case["name"]))
def test_force_balance_regression_cases(case: dict[str, Any]) -> None:
    question = normalize(SolveRequest(question=str(case["question"])))
    result = ForceBalanceSkill().solve(question)

    assert question.subject == case["expected_subject"]
    assert classify(question) == case["expected_question_type"]
    assert result.skill == case["expected_skill"]
    assert result.question_type == case["expected_question_type"]
    assert all(isinstance(step, Step) for step in result.steps)
    assert case["expected_answer_contains"] in str(result.answer)
    assert result.student_explanation is not None
    assert case["expected_summary_contains"] in result.student_explanation.summary


def test_force_balance_rejects_missing_direction() -> None:
    question = normalize(SolveRequest(question="求 10 N 力的平衡力"))

    with pytest.raises(ValueError, match="direction"):
        ForceBalanceSkill().solve(question)
