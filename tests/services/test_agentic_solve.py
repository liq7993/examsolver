import pytest

from _helpers.fake_llm import FakeLLMClient
from examsolver.contracts import NormalizedQuestion
from examsolver.services.agentic_solve import agentic_solve
from examsolver.skills.base import SkillExecutionError


def _normalized(text: str, subject: str = "calculus") -> NormalizedQuestion:
    return NormalizedQuestion(
        raw_text=text,
        normalized_text=text,
        subject=subject,
        hints={"request_id": "rid", "solve_id": "sid"},
    )


# ---- deterministic decomposition: recognized patterns, no LLM needed -------------


def test_second_derivative_is_decomposed_deterministically_without_llm() -> None:
    result = agentic_solve(_normalized("求 x^3 的二阶导数"), llm=None)

    assert result.skill == "agentic.multi_step"
    assert result.question_type == "multi_step"
    assert len(result.steps) == 2
    assert result.meta["agentic.plan_source"] == "deterministic"
    # d/dx(x^3)=3x^2; d/dx(3x^2)=6x
    assert "6 x" in str(result.answer)


def test_third_derivative_chains_three_steps_without_llm() -> None:
    result = agentic_solve(_normalized("求 x^5 的三阶导数"), llm=None)

    assert len(result.steps) == 3
    assert result.meta["agentic.plan_source"] == "deterministic"
    assert "60 x^{2}" in str(result.answer)


def test_matrix_chain_is_decomposed_deterministically_without_llm() -> None:
    result = agentic_solve(
        _normalized(
            "计算 [[1,2],[3,4]] 乘 [[5,6],[7,8]] 再乘 [[1,0],[1,1]]",
            subject="linear_algebra",
        ),
        llm=None,
    )

    assert result.meta["agentic.plan_source"] == "deterministic"
    # [[1,2],[3,4]]·[[5,6],[7,8]] = [[19,22],[43,50]]; ·[[1,0],[1,1]] = [[41,22],[93,50]]
    answer = str(result.answer)
    assert "41 & 22" in answer and "93 & 50" in answer


# ---- LLM planner fallback: unrecognized multi-step shapes ------------------------


def test_llm_planner_handles_unrecognized_multistep() -> None:
    # A shape the deterministic decomposer does not recognize -> the LLM planner
    # drives, but every leaf still runs a deterministic skill.
    planner = FakeLLMClient.from_recorded(
        {
            "steps": [
                {"goal": "求 x^3 的导数", "subject": "calculus", "question_type": "derivative"},
                {"goal": "求 {{prev}} 的导数", "subject": "calculus", "question_type": "derivative"},
            ]
        }
    )

    result = agentic_solve(_normalized("请把这道多步题拆开依次求解"), llm=planner)

    assert result.skill == "agentic.multi_step"
    assert result.meta["agentic.plan_source"] == "llm"
    assert "6 x" in str(result.answer)


def test_unrecognized_shape_without_llm_degrades() -> None:
    with pytest.raises(SkillExecutionError):
        agentic_solve(_normalized("请把这道多步题拆开依次求解"), llm=None)


def test_llm_empty_plan_degrades() -> None:
    planner = FakeLLMClient.from_recorded({"steps": []})

    with pytest.raises(SkillExecutionError):
        agentic_solve(_normalized("请把这道多步题拆开依次求解"), llm=planner)


def test_unsolvable_step_degrades_without_fabricating() -> None:
    # A step the derivative skill cannot parse must abort (retry then raise),
    # never invent an answer.
    planner = FakeLLMClient.from_recorded(
        {
            "steps": [
                {"goal": "请描述一下今天的天气", "subject": "calculus", "question_type": "derivative"},
            ]
        }
    )

    with pytest.raises(SkillExecutionError):
        agentic_solve(_normalized("请把这道多步题拆开依次求解"), llm=planner)
