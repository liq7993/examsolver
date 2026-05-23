from examsolver.contracts import SolveRequest
from examsolver.pipeline.classifier import classify
from examsolver.pipeline.normalizer import normalize


def test_classifies_derivative_question() -> None:
    question = normalize(SolveRequest(question="求 x^2 对 x 的导数"))
    assert classify(question) == "derivative"


def test_classifies_latex_derivative_question() -> None:
    question = normalize(SolveRequest(question="计算 $\\frac{d}{dx}x^2$"))
    assert classify(question) == "derivative"


def test_unknown_when_no_rule_matches() -> None:
    question = normalize(SolveRequest(question="解释一下今天的天气"))
    assert classify(question) == "unknown"


def test_classifies_matrix_multiplication_question() -> None:
    question = normalize(SolveRequest(question="计算矩阵 [[1,2],[3,4]] 乘 [[5,6],[7,8]]"))
    assert classify(question) == "matrix_mul"


def test_classifies_force_balance_question() -> None:
    question = normalize(SolveRequest(question="一个 10N 的力向右作用，求它的平衡力。"))
    assert classify(question) == "force_balance"
