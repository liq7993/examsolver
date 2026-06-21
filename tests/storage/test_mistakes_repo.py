from __future__ import annotations

from examsolver.contracts import SolveRequest, SolveResponse
from examsolver.pipeline.classifier import classify
from examsolver.pipeline.dispatcher import dispatch_or_unknown
from examsolver.pipeline.formatter import format_response
from examsolver.pipeline.normalizer import normalize
from examsolver.storage.history_repo import save_history
from examsolver.storage.mistakes_repo import (
    add_mistake_for_solve,
    delete_mistake,
    export_mistakes_markdown,
    list_mistakes,
    record_review,
    update_user_note,
)


def test_mistakes_repo_crud_flow() -> None:
    response = _save_solve("求 x^2 对 x 的导数")

    created = add_mistake_for_solve(response.solve_id, user_note="指数法则写错")
    assert created is not None
    assert created.solve_id == response.solve_id
    assert created.subject == "calculus"
    assert created.question_type == "derivative"
    assert created.user_note == "指数法则写错"
    assert created.review_count == 0
    assert created.last_review is None

    page = list_mistakes()
    assert page == [created]
    assert list_mistakes(subject="calculus") == [created]
    assert list_mistakes(subject="mechanism") == []

    updated = update_user_note(created.id, "复习幂函数求导")
    assert updated is not None
    assert updated.user_note == "复习幂函数求导"

    assert delete_mistake(created.id) is True
    assert list_mistakes() == []


def test_record_review_bumps_count_and_stamps_time() -> None:
    response = _save_solve("求 x^2 对 x 的导数")
    created = add_mistake_for_solve(response.solve_id)
    assert created is not None
    assert created.review_count == 0
    assert created.last_review is None

    reviewed = record_review(created.id)
    assert reviewed is not None
    assert reviewed.review_count == 1
    assert reviewed.last_review is not None

    reviewed_again = record_review(created.id)
    assert reviewed_again is not None
    assert reviewed_again.review_count == 2
    assert list_mistakes()[0].review_count == 2


def test_mistakes_repo_missing_rows_return_none_or_false() -> None:
    assert add_mistake_for_solve("missing") is None
    assert update_user_note("missing", "note") is None
    assert record_review("missing") is None
    assert delete_mistake("missing") is False


def test_mistakes_export_markdown() -> None:
    response = _save_solve("求 x^2 对 x 的导数")
    created = add_mistake_for_solve(response.solve_id, user_note="链式法则混淆")
    assert created is not None

    body = export_mistakes_markdown()

    assert "# 错题本" in body
    assert response.solve_id in body
    assert created.id in body
    assert "链式法则混淆" in body


def _save_solve(question_text: str) -> SolveResponse:
    question = normalize(SolveRequest(question=question_text))
    result = dispatch_or_unknown(question, classify(question))
    response = format_response(question, result)
    save_history(question=question, response=response)
    return response
