from examsolver.contracts import SolveRequest, Step
from examsolver.pipeline.normalizer import normalize
from examsolver.skills.linear_algebra import MatrixMulSkill


def test_matrix_mul_skill_multiplies_two_matrices() -> None:
    question = normalize(SolveRequest(question="计算矩阵 [[1,2],[3,4]] 乘 [[5,6],[7,8]]"))
    result = MatrixMulSkill().solve(question)

    assert result.skill == "linear_algebra.matrix_mul"
    assert all(isinstance(step, Step) for step in result.steps)
    assert result.answer == "$\\begin{bmatrix} 19 & 22 \\\\ 43 & 50 \\end{bmatrix}$"
    assert result.student_explanation is not None


def test_matrix_mul_skill_rejects_misaligned_matrices() -> None:
    question = normalize(SolveRequest(question="计算矩阵 [[1,2]] 乘 [[1,2]]"))

    try:
        MatrixMulSkill().solve(question)
    except ValueError as exc:
        assert "dimensions" in str(exc)
    else:
        raise AssertionError("expected ValueError")
