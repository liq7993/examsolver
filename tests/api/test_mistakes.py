from __future__ import annotations

from fastapi import BackgroundTasks, HTTPException

from examsolver.api.routes.mistakes import (
    add_mistake,
    export_mistakes,
    get_mistakes,
    patch_mistake,
    remove_mistake,
    review_mistake,
)
from examsolver.api.routes.solve import solve_question
from examsolver.api.schemas import AddMistakeRequestBody, SolveRequestBody, UpdateMistakeRequestBody


def test_mistakes_api_crud_flow() -> None:
    solved = solve_question(SolveRequestBody(question="求 x^2 对 x 的导数"), BackgroundTasks())

    created = add_mistake(
        AddMistakeRequestBody(solve_id=solved.solve_id, user_note="答案忘记化简")
    )
    assert created.solve_id == solved.solve_id
    assert created.subject == "calculus"
    assert get_mistakes()[0].id == created.id
    assert get_mistakes(subject="calculus")[0].id == created.id

    updated = patch_mistake(
        created.id,
        UpdateMistakeRequestBody(user_note="复查求导公式"),
    )
    assert updated.user_note == "复查求导公式"

    exported = export_mistakes(subject="calculus")
    body = bytes(exported.body).decode("utf-8")
    assert exported.media_type == "text/markdown; charset=utf-8"
    assert solved.solve_id in body
    assert "复查求导公式" in body

    assert remove_mistake(created.id) == {"deleted": True}
    assert get_mistakes() == []


def test_mistakes_api_review_bumps_count_and_stamps_time() -> None:
    solved = solve_question(SolveRequestBody(question="求 x^2 对 x 的导数"), BackgroundTasks())
    created = add_mistake(AddMistakeRequestBody(solve_id=solved.solve_id))
    assert created.review_count == 0
    assert created.last_review is None

    reviewed = review_mistake(created.id)
    assert reviewed.id == created.id
    assert reviewed.review_count == 1
    assert reviewed.last_review is not None
    assert get_mistakes()[0].review_count == 1

    remove_mistake(created.id)


def test_mistakes_api_raises_404_for_missing_solve() -> None:
    try:
        add_mistake(AddMistakeRequestBody(solve_id="missing"))
    except HTTPException as exc:
        assert exc.status_code == 404
        assert exc.detail == "solve_id not found"
    else:
        raise AssertionError("expected HTTPException")


def test_mistakes_api_raises_404_for_missing_mistake_id() -> None:
    for action in (
        lambda: patch_mistake("missing", UpdateMistakeRequestBody(user_note="x")),
        lambda: review_mistake("missing"),
        lambda: remove_mistake("missing"),
    ):
        try:
            action()
        except HTTPException as exc:
            assert exc.status_code == 404
        else:
            raise AssertionError("expected HTTPException")
