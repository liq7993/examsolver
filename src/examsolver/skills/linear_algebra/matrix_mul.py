"""Linear algebra matrix multiplication skill."""

from __future__ import annotations

import ast
from dataclasses import dataclass

from examsolver.contracts import NormalizedQuestion, SolveResult, Step, StudentExplanation

Matrix = list[list[int]]


@dataclass(frozen=True, slots=True)
class MatrixPair:
    left: Matrix
    right: Matrix


class MatrixMulSkill:
    """Multiply two small integer matrices written as Python-style nested lists."""

    name = "linear_algebra.matrix_mul"
    version = "0.1.0"
    subject = "linear_algebra"
    question_types = ["matrix_mul"]

    def can_handle(self, question: NormalizedQuestion) -> bool:
        text = question.normalized_text.lower()
        return ("矩阵" in text and "乘" in text) or "matrix" in text

    def solve(self, question: NormalizedQuestion) -> SolveResult:
        pair = _extract_matrix_pair(question.normalized_text)
        product = _multiply(pair.left, pair.right)
        left_shape = _shape(pair.left)
        right_shape = _shape(pair.right)
        product_shape = _shape(product)

        answer = _format_latex_matrix(product)
        return SolveResult(
            question_type="matrix_mul",
            skill=self.name,
            steps=[
                Step(
                    index=1,
                    description="识别矩阵维度",
                    formula_latex=(
                        rf"{left_shape[0]}\times {left_shape[1]}"
                        rf"\quad\text{{and}}\quad"
                        rf"{right_shape[0]}\times {right_shape[1]}"
                    ),
                ),
                Step(
                    index=2,
                    description="检查矩阵乘法维度条件",
                    formula_latex=rf"{left_shape[1]}={right_shape[0]}",
                ),
                Step(
                    index=3,
                    description="逐项做行列点积，得到结果矩阵",
                    formula_latex=rf"{product_shape[0]}\times {product_shape[1]}",
                ),
            ],
            answer=answer,
            student_explanation=StudentExplanation(
                summary="这题是在计算两个矩阵的乘积。",
                intuition="结果矩阵里的每个数，都来自左矩阵的一行和右矩阵的一列做点积。",
                step_by_step=[
                    "先检查维度是否匹配。",
                    "再用左矩阵第 i 行乘右矩阵第 j 列，得到结果的第 i 行第 j 列。",
                    f"本题结果是 {answer}。",
                ],
                common_mistake="常见错误是把矩阵乘法当成对应位置相乘；矩阵乘法用的是行列点积。",
                self_check_question="结果矩阵的行数和列数分别来自哪一个原矩阵？",
            ),
            meta={
                "success": True,
                "skill_version": self.version,
                "message": "已完成矩阵乘法。",
                "linear_algebra.matrix_mul.left_shape": left_shape,
                "linear_algebra.matrix_mul.right_shape": right_shape,
                "linear_algebra.matrix_mul.product_shape": product_shape,
                # Clean, parser-round-trippable result for agentic chaining
                # (repr -> "[[19, 22], [43, 50]]", which _parse_matrix accepts back).
                "result": repr(product),
            },
        )


def _extract_matrix_pair(text: str) -> MatrixPair:
    literals = _extract_matrix_literals(text)
    if len(literals) < 2:
        raise ValueError("matrix multiplication requires two matrices")
    left = _parse_matrix(literals[0])
    right = _parse_matrix(literals[1])
    if _shape(left)[1] != _shape(right)[0]:
        raise ValueError("matrix dimensions do not align")
    return MatrixPair(left=left, right=right)


def _extract_matrix_literals(text: str) -> list[str]:
    literals: list[str] = []
    index = 0
    while index < len(text):
        start = text.find("[[", index)
        if start == -1:
            break
        depth = 0
        end = start
        while end < len(text):
            char = text[end]
            if char == "[":
                depth += 1
            elif char == "]":
                depth -= 1
                if depth == 0:
                    literals.append(text[start : end + 1])
                    index = end + 1
                    break
            end += 1
        else:
            break
    return literals


def _parse_matrix(literal: str) -> Matrix:
    value = ast.literal_eval(literal)
    if not isinstance(value, list) or not value:
        raise ValueError("matrix must be a non-empty list")

    matrix: Matrix = []
    width: int | None = None
    for row in value:
        if not isinstance(row, list) or not row:
            raise ValueError("matrix rows must be non-empty lists")
        parsed_row: list[int] = []
        for item in row:
            if not isinstance(item, int):
                raise ValueError("matrix entries must be integers")
            parsed_row.append(item)
        width = len(parsed_row) if width is None else width
        if len(parsed_row) != width:
            raise ValueError("matrix rows must have equal length")
        matrix.append(parsed_row)
    return matrix


def _shape(matrix: Matrix) -> tuple[int, int]:
    return (len(matrix), len(matrix[0]))


def _multiply(left: Matrix, right: Matrix) -> Matrix:
    rows = len(left)
    cols = len(right[0])
    shared = len(right)
    return [
        [sum(left[row][k] * right[k][col] for k in range(shared)) for col in range(cols)]
        for row in range(rows)
    ]


def _format_latex_matrix(matrix: Matrix) -> str:
    rows = [" & ".join(str(item) for item in row) for row in matrix]
    body = r" \\ ".join(rows)
    return f"$\\begin{{bmatrix}} {body} \\end{{bmatrix}}$"
