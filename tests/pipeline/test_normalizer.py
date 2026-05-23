from examsolver.contracts import SolveRequest
from examsolver.pipeline.normalizer import normalize


def test_normalize_generates_ids_and_latex_hints() -> None:
    question = normalize(SolveRequest(question="求 $x^2$ 对 x 的导数"))

    assert question.subject == "calculus"
    assert len(question.hints["request_id"]) == 32
    assert len(question.hints["solve_id"]) == 32
    assert question.hints["has_latex"] is True
    assert question.hints["latex_segments"] == 1


def test_same_question_gets_different_solve_ids() -> None:
    first = normalize(SolveRequest(question="求 x^2 对 x 的导数"))
    second = normalize(SolveRequest(question="求 x^2 对 x 的导数"))

    assert first.hints["solve_id"] != second.hints["solve_id"]
