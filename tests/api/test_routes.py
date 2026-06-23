from pathlib import Path

from fastapi import BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from pytest import MonkeyPatch
from starlette.responses import Response

from examsolver.api.app import STATIC_DIR, create_app
from examsolver.contracts import Flashcard
from examsolver.api.routes.capabilities import capabilities
from examsolver.api.routes.export import export_docx, export_markdown, export_pdf
from examsolver.api.routes.health import health, info, ready
from examsolver.api.routes.llm import local_llm_status
from examsolver.api.routes.solve import get_solve, solve_history, solve_question
from examsolver.api.schemas import SolveRequestBody
from examsolver.skills.base import PersistenceError


def test_health_route() -> None:
    assert health() == {"status": "ok"}


def test_local_dev_cors_allows_non_default_frontend_port() -> None:
    app = create_app()
    cors_middleware = next(
        middleware
        for middleware in app.user_middleware
        if getattr(middleware, "cls", None) is CORSMiddleware
    )

    assert cors_middleware.kwargs["allow_origin_regex"] == (
        r"^http://(localhost|127\.0\.0\.1):\d+$"
    )


def test_ready_route_reports_dependencies(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("EXAMSOLVER_DB_PATH", ":memory:")
    response = Response()

    payload = ready(response)

    assert response.status_code == 200
    assert payload["status"] == "ready"
    assert payload["checks"]["database"]["ok"] is True
    assert payload["checks"]["registry"]["skill_count"] >= 3


def test_ready_route_returns_503_when_database_is_unavailable(monkeypatch: MonkeyPatch) -> None:
    def fail_connect() -> None:
        raise PersistenceError("database unavailable")

    monkeypatch.setattr("examsolver.api.routes.health.connect", fail_connect)
    response = Response()

    payload = ready(response)

    assert response.status_code == 503
    assert payload["status"] == "not_ready"
    assert payload["checks"]["database"]["ok"] is False
    assert payload["checks"]["database"]["error"] == "database unavailable"


def test_info_route_reports_runtime_snapshot(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("EXAMSOLVER_GIT_SHA", "abc123")

    payload = info()

    assert payload["name"] == "Examsolver"
    assert payload["git_sha"] == "abc123"
    assert payload["skill_count"] >= 3
    assert "mechanics.force_balance" in payload["skills"]
    assert isinstance(payload["uptime_seconds"], float)


def test_capabilities_route_lists_registered_skills() -> None:
    response = capabilities()

    skill_names = {skill.name for skill in response.skills}
    assert "calculus.derivative" in skill_names
    assert "linear_algebra.matrix_mul" in skill_names
    assert "mechanics.force_balance" in skill_names
    subjects = {subject.name: subject.question_types for subject in response.subjects}
    assert subjects["calculus"] == ["derivative"]
    assert subjects["general"] == ["general", "unknown"]
    assert subjects["linear_algebra"] == ["matrix_mul"]
    assert subjects["mechanics"] == ["force_balance"]


def test_llm_status_route_reports_local_gemma_configuration(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    # Use a real temp file so model_path_exists is OS-independent (any hardcoded
    # absolute path would only exist on the dev machine and break elsewhere).
    model_file = tmp_path / "gemma-4-E2B-it-Q4_K_M.gguf"
    model_file.write_bytes(b"")
    monkeypatch.setenv("EXAMSOLVER_LLM_PROVIDER", "local_gguf")
    monkeypatch.setenv("EXAMSOLVER_LLM_BASE_URL", "http://127.0.0.1:8080/v1")
    monkeypatch.setenv("EXAMSOLVER_LLM_MODEL", "gemma-4-E2B-it-Q4_K_M")
    monkeypatch.setenv("EXAMSOLVER_LLM_MODEL_PATH", str(model_file))
    monkeypatch.setattr(
        "examsolver.services.explanation.probe_local_llm",
        lambda config: {
            "server_reachable": True,
            "server_model_count": 1,
            "server_error": None,
        },
    )

    response = local_llm_status()

    assert response.enabled is True
    assert response.provider == "local_gguf"
    assert response.model == "gemma-4-E2B-it-Q4_K_M"
    assert response.model_path_exists is True
    assert response.server_reachable is True
    assert response.server_model_count == 1


def test_solve_route_delegates_to_service() -> None:
    response = solve_question(SolveRequestBody(question="求 x^2 对 x 的导数"), BackgroundTasks())

    assert response.success is True
    assert response.question_type == "derivative"
    assert response.skill == "calculus.derivative"
    assert response.answer == "$\\frac{d}{dx}\\left(x^{2}\\right) = 2 x$"
    assert response.note is not None
    assert response.note.question_latex == "求 x^2 对 x 的导数"
    assert response.note.steps[0].description


def test_solve_route_returns_deterministic_function_plot() -> None:
    response = solve_question(SolveRequestBody(question="求 x^2 对 x 的导数"), BackgroundTasks())

    assert response.plot is not None
    assert response.plot.x_label == "x"
    assert [series.label for series in response.plot.series] == ["f(x)", "f'(x)"]
    assert len(response.plot.series[0].points) > 2


def test_solve_route_has_no_plot_for_non_function_questions() -> None:
    response = solve_question(
        SolveRequestBody(question="计算矩阵 [[1,2],[3,4]] 乘以 [[5,6],[7,8]]"),
        BackgroundTasks(),
    )

    assert response.plot is None


def test_solve_history_and_get_solve_routes() -> None:
    solved = solve_question(SolveRequestBody(question="求 x^2 对 x 的导数"), BackgroundTasks())

    page = solve_history(limit=10, offset=0)
    assert len(page.items) == 1
    assert page.items[0].solve_id == solved.solve_id

    stored = get_solve(solved.solve_id)
    assert stored.answer == solved.answer


def test_solve_route_runs_flashcards_in_the_background(monkeypatch: MonkeyPatch) -> None:
    cards = [
        Flashcard(front="d/dx x^2?", back="2x", card_type="formula"),
        Flashcard(front="幂法则?", back="n x^(n-1)", card_type="concept"),
    ]
    monkeypatch.setattr("examsolver.services.solve_service.pick_llm", lambda *_a, **_k: None)
    monkeypatch.setattr(
        "examsolver.services.solve_service.generate_flashcards",
        lambda _note, *, llm: cards,
    )
    client = TestClient(create_app())

    posted = client.post("/solve", json={"question": "求 x^2 对 x 的导数"})
    assert posted.status_code == 200
    body = posted.json()
    assert body["note"]["flashcards"] == []  # kept off the hot path

    # TestClient runs background tasks after the response, so cards are persisted now.
    fetched = client.get(f"/solve/{body['solve_id']}")
    assert fetched.status_code == 200
    assert [c["front"] for c in fetched.json()["note"]["flashcards"]] == ["d/dx x^2?", "幂法则?"]


def test_export_markdown_route_returns_stored_solve_artifact() -> None:
    solved = solve_question(SolveRequestBody(question="求 x^2 对 x 的导数"), BackgroundTasks())

    response = export_markdown(solved.solve_id)

    assert response.media_type == "text/markdown; charset=utf-8"
    assert "attachment; filename=" in response.headers["Content-Disposition"]
    body = bytes(response.body).decode("utf-8")
    assert "## 题目" in body
    assert "求 x^2 对 x 的导数" in body
    assert "$\\frac{d}{dx}\\left(x^{2}\\right) = 2 x$" in body


def test_export_markdown_route_raises_404_for_missing_id() -> None:
    try:
        export_markdown("missing")
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError("expected HTTPException")


def test_export_docx_route_returns_editable_word_file() -> None:
    solved = solve_question(SolveRequestBody(question="求 x^2 对 x 的导数"), BackgroundTasks())

    response = export_docx(solved.solve_id)

    assert response.media_type == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert bytes(response.body).startswith(b"PK")
    assert "filename*=UTF-8''" in response.headers["Content-Disposition"]
    assert ".docx" in response.headers["Content-Disposition"]


def test_export_docx_route_raises_404_for_missing_id() -> None:
    try:
        export_docx("missing")
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError("expected HTTPException")


def test_export_pdf_route_returns_print_quality_pdf() -> None:
    solved = solve_question(SolveRequestBody(question="求 x^2 对 x 的导数"), BackgroundTasks())

    response = export_pdf(solved.solve_id)

    assert response.media_type == "application/pdf"
    assert bytes(response.body).startswith(b"%PDF-")
    assert "filename*=UTF-8''" in response.headers["Content-Disposition"]
    assert ".pdf" in response.headers["Content-Disposition"]


def test_export_pdf_route_raises_404_for_missing_id() -> None:
    try:
        export_pdf("missing")
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError("expected HTTPException")


def test_get_solve_raises_404_for_missing_id() -> None:
    try:
        get_solve("missing")
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError("expected HTTPException")


def test_frontend_static_shell_is_served() -> None:
    app = create_app()
    route_names = {getattr(route, "name", None) for route in app.routes}

    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    script = (STATIC_DIR / "app.js").read_text(encoding="utf-8")

    assert "frontend_index" in route_names
    assert "frontend_head" in route_names
    assert "frontend_static" in route_names
    assert "export_markdown" in route_names
    assert "local_llm_status" in route_names
    assert "ExamSolver" in html
    assert "单题求解工作台" in html
    assert 'href="/static/vendor/katex/katex.min.css"' in html
    assert 'href="/static/app.css"' in html
    assert 'src="/static/vendor/katex/katex.min.js"' in html
    assert 'src="/static/app.js"' in html
    assert "formulas-panel" in html
    assert "result-status" in html
    assert "page-tools" in html
    assert "下载 Markdown" in html
    assert "导出 PDF" in html
    assert "solveQuestion" in script
    assert "renderLatex" in script
    assert "renderMathText" in script
    assert "window.katex" in script
    assert "编辑 LaTeX" in script
    assert "data-copy-formula" in script
    assert "copyText" in script
    assert "noteMarkdown" in script
    assert "markdownArtifact" in script
    assert "/export.md" in script
    assert "/export.pdf" in script
    assert "downloadText" in script
    assert "resizeComposer" in script
    assert 'id="open-settings"' in html
    assert 'id="settings-overlay"' in html
    assert 'id="provider-select"' in html
    assert 'id="tutorial-overlay"' in html
    assert "消费上限" in html
    assert "不要泄露" in html
    assert "loadConfig" in script
    assert "saveSettings" in script
    assert "/config" in script
    assert "examsolver:onboarded" in script
    assert 'id="collapse-sidebar"' in html
    assert 'id="expand-sidebar"' in html
    assert "sidebar-collapsed" in script
    assert "examsolver:sidebar-collapsed" in script
    assert 'id="subject-cards"' in html
    assert 'id="project-view"' in html
    assert 'id="project-back"' in html
    assert "科目项目" in html
    assert "loadCapabilities" in script
    assert "renderSubjectCards" in script
    assert "renderProjectView" in script
    assert "/solve/capabilities" in script
    assert "data-subject" in script
    assert 'id="plot-panel"' in html
    assert 'id="plot-body"' in html
    assert "函数图像" in html
    assert "buildPlotSvg" in script
    assert "renderPlot" in script
    assert 'id="open-mistakes"' in html
    assert 'id="mistakes-view"' in html
    assert 'id="add-mistake"' in html
    assert "错题本" in html
    assert "loadMistakes" in script
    assert "renderMistakes" in script
    assert "addCurrentMistake" in script
    assert "saveMistakeNote" in script
    assert "reviewMistake" in script
    assert "data-review-mistake" in script
    assert "/review" in script
    assert "/mistakes" in script
    assert "/mistakes/export.md" in script
