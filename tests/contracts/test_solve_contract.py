from dataclasses import fields, is_dataclass

from examsolver.contracts import (
    Citation,
    NormalizedQuestion,
    SolveRequest,
    SolveResponse,
    SolveResult,
    Step,
    StudentExplanation,
)


def test_contracts_are_dataclasses() -> None:
    assert is_dataclass(SolveRequest)
    assert is_dataclass(NormalizedQuestion)
    assert is_dataclass(Step)
    assert is_dataclass(Citation)
    assert is_dataclass(StudentExplanation)
    assert is_dataclass(SolveResult)
    assert is_dataclass(SolveResponse)


def test_solve_response_shape_includes_solve_id() -> None:
    names = [field.name for field in fields(SolveResponse)]
    assert names[:9] == [
        "success",
        "solve_id",
        "subject",
        "question_type",
        "skill",
        "steps",
        "answer",
        "message",
        "student_explanation",
    ]
    assert {"citations", "fallback_reasons", "diagnostics", "note"}.issubset(names)
