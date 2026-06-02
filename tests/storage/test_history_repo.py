from examsolver.contracts import SolveRequest
from examsolver.pipeline.classifier import classify
from examsolver.pipeline.dispatcher import dispatch_or_unknown
from examsolver.pipeline.formatter import format_response
from examsolver.pipeline.normalizer import normalize
from examsolver.storage.history_repo import get_response, get_snapshot, list_history, save_history


def test_save_list_and_get_history() -> None:
    question = normalize(SolveRequest(question="求 x^2 对 x 的导数"))
    result = dispatch_or_unknown(question, classify(question))
    response = format_response(question, result)

    save_history(question=question, response=response)

    page = list_history(limit=10)
    assert page.has_more is False
    assert page.next_offset is None
    assert len(page.items) == 1
    assert page.items[0].solve_id == response.solve_id
    assert page.items[0].question_snippet == "求 x^2 对 x 的导数"

    stored = get_response(response.solve_id)
    assert stored is not None
    assert stored.solve_id == response.solve_id
    assert stored.answer == "$\\frac{d}{dx}\\left(x^{2}\\right) = 2 x$"

    snapshot = get_snapshot(response.solve_id)
    assert snapshot is not None
    assert snapshot.question == "求 x^2 对 x 的导数"
    assert snapshot.response.solve_id == response.solve_id


def test_history_pagination_reports_next_offset() -> None:
    for index in range(3):
        question = normalize(SolveRequest(question=f"求 x^{index + 2} 对 x 的导数"))
        response = format_response(question, dispatch_or_unknown(question, classify(question)))
        save_history(question=question, response=response)

    page = list_history(limit=2, offset=0)

    assert len(page.items) == 2
    assert page.has_more is True
    assert page.next_offset == 2
