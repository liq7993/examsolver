import pytest

from examsolver.contracts import NormalizedQuestion
from examsolver.graph.nodes import general_node, skill_node


def test_skill_node_writes_solve_result_for_known_skill() -> None:
    state = skill_node(
        {
            "normalized": NormalizedQuestion(
                raw_text="求 x^2 对 x 的导数",
                normalized_text="求 x^2 对 x 的导数",
                subject="calculus",
                hints={"request_id": "rid-1"},
            ),
            "question_type": "derivative",
        }
    )

    assert state["solve_result"].skill == "calculus.derivative"


def test_general_node_writes_general_cot_result() -> None:
    state = general_node(
        {
            "normalized": NormalizedQuestion(
                raw_text="汽车 ABS 起到什么作用？",
                normalized_text="汽车 ABS 起到什么作用？",
                subject="unknown",
                hints={"request_id": "rid-1"},
            )
        }
    )

    assert state["solve_result"].skill == "general.cot_with_textbook"
    assert state["solve_result"].answer is not None
    assert state["solve_result"].meta["common_mistakes"]


def test_general_node_falls_back_to_unknown_on_general_skill_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("examsolver.graph.nodes.pick_llm", lambda *_args, **_kwargs: None)

    state = general_node(
        {
            "normalized": NormalizedQuestion(
                raw_text="解释天气",
                normalized_text="解释天气",
                subject="unknown",
                hints={"request_id": "rid-1"},
            )
        }
    )

    assert state["solve_result"].skill == "unknown"
    assert state["fallback_reasons"] == ["general_skill_failed"]


def test_skill_node_records_fallback_reason_on_skill_failure() -> None:
    state = skill_node(
        {
            "normalized": NormalizedQuestion(
                raw_text="计算矩阵 [[1,2]] 乘 [[1,2]]",
                normalized_text="计算矩阵 [[1,2]] 乘 [[1,2]]",
                subject="linear_algebra",
                hints={"request_id": "rid-1"},
            ),
            "question_type": "matrix_mul",
        }
    )

    assert state["solve_result"].skill == "unknown"
    assert state["fallback_reasons"] == ["primary_skill_failed"]
