from collections.abc import Sequence
from typing import get_args, get_origin, get_type_hints

from examsolver.contracts import Citation, SolveRequest, SolveResult, Step


def test_solve_request_accepts_image_paths() -> None:
    request = SolveRequest(question="q", image_paths=["/tmp/q.png"])

    assert request.image_paths == ["/tmp/q.png"]


def test_solve_result_steps_are_structured_steps() -> None:
    hints = get_type_hints(SolveResult)
    steps_type = hints["steps"]

    assert get_origin(steps_type) is Sequence
    assert get_args(steps_type) == (Step,)


def test_step_and_citation_shapes_are_stable() -> None:
    step = Step(index=1, description="识别表达式", formula_latex="x^2")
    citation = Citation(source="book.pdf", chunk_id="c1", page=3, snippet="text")

    assert step.image_hint is None
    assert citation.page == 3
