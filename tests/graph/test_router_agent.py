import pytest

from examsolver.contracts import SolveRequest
from examsolver.graph.router_agent import route_question
from examsolver.pipeline.normalizer import normalize


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
    assert expected_type in decision.reasoning


def test_route_question_sends_unknown_to_general_placeholder() -> None:
    decision = route_question(normalize(SolveRequest(question="解释一下今天的天气")))

    assert decision.subject == "general"
    assert decision.question_type == "unknown"
    assert decision.confidence == 0.0
    assert "M2" in decision.reasoning
