from examsolver.contracts import SolveRequest
from examsolver.pipeline.dispatcher import dispatch_or_unknown
from examsolver.pipeline.normalizer import normalize


def test_dispatches_derivative_skill() -> None:
    question = normalize(SolveRequest(question="求 x^2 对 x 的导数"))
    result = dispatch_or_unknown(question, "derivative")

    assert result.skill == "calculus.derivative"
    assert result.question_type == "derivative"


def test_dispatches_unknown_skill() -> None:
    question = normalize(SolveRequest(question="解释一下今天的天气"))
    result = dispatch_or_unknown(question, "unknown")

    assert result.skill == "unknown"
    assert result.meta["success"] is False


def test_dispatches_matrix_mul_skill() -> None:
    question = normalize(SolveRequest(question="计算矩阵 [[1,2],[3,4]] 乘 [[5,6],[7,8]]"))
    result = dispatch_or_unknown(question, "matrix_mul")

    assert result.skill == "linear_algebra.matrix_mul"
    assert result.question_type == "matrix_mul"


def test_dispatches_force_balance_skill() -> None:
    question = normalize(SolveRequest(question="一个 10 N 的力向右作用，求它的平衡力。"))
    result = dispatch_or_unknown(question, "force_balance")

    assert result.skill == "mechanics.force_balance"
    assert result.question_type == "force_balance"
