import pytest

from examsolver.contracts import SolveRequest
from examsolver.graph.router_agent import route_question
from examsolver.pipeline.normalizer import normalize
from _helpers.fake_llm import FakeLLMClient


@pytest.mark.parametrize(
    ("question_text", "expected_subject", "expected_type"),
    [
        ("求 x^2 对 x 的导数", "calculus", "derivative"),
        ("计算矩阵 [[1,2],[3,4]] 乘 [[5,6],[7,8]]", "linear_algebra", "matrix_mul"),
        ("一个 10N 的力向右作用，求它的平衡力。", "mechanics", "force_balance"),
    ],
)
def test_route_question_uses_deterministic_classifier_for_known_types(
    question_text: str,
    expected_subject: str,
    expected_type: str,
) -> None:
    decision = route_question(normalize(SolveRequest(question=question_text)))

    assert decision.subject == expected_subject
    assert decision.question_type == expected_type
    assert decision.confidence == 1.0
    assert decision.reasoning == "regex"


def test_route_question_uses_llm_when_regex_does_not_match() -> None:
    client = FakeLLMClient.from_recorded(
        {
            "subject": "auto_theory",
            "question_type": "force_balance",
            "confidence": 0.82,
            "reasoning": "LLM matched a supported route.",
        }
    )

    decision = route_question(
        normalize(SolveRequest(question="汽车制动时的受力如何分析？")),
        llm_client=client,
    )

    assert decision.subject == "auto_theory"
    assert decision.question_type == "force_balance"
    assert decision.confidence == 0.82
    assert decision.reasoning == "LLM matched a supported route."
    assert client.call_count == 1
    assert client.last_json_schema is not None


def test_route_question_sends_unknown_to_general_when_llm_cannot_decide() -> None:
    client = FakeLLMClient.from_recorded(
        {
            "subject": "general",
            "question_type": "unknown",
            "confidence": 0,
            "reasoning": "not enough signal",
        }
    )

    decision = route_question(
        normalize(SolveRequest(question="解释一下今天的天气")),
        llm_client=client,
    )

    assert decision.subject == "general"
    assert decision.question_type == "unknown"
    assert decision.confidence == 0.0
    assert decision.fallback_reasons == ("llm_router_unknown",)
