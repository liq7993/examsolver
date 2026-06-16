from pathlib import Path

from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pytest import MonkeyPatch
from starlette.responses import Response

from examsolver.api.app import STATIC_DIR, create_app
from examsolver.api.routes.capabilities import capabilities
from examsolver.api.routes.export import export_docx, export_markdown
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
        middleware for middleware in app.user_middleware if middleware.cls is CORSMiddleware
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
    response = solve_question(SolveRequestBody(question="求 x^2 对 x 的导数"))

    assert response.success is True
    assert response.question_type == "derivative"
    assert response.skill == "calculus.derivative"
    assert response.answer == "$\\frac{d}{dx}\\left(x^{2}\\right) = 2 x$"
    assert response.note is not None
    assert response.note.question_latex == "求 x^2 对 x 的导数"
    assert response.note.steps[0].description


def test_solve_history_and_get_solve_routes() -> None:
    solved = solve_question(SolveRequestBody(question="求 x^2 对 x 的导数"))

    page = solve_history(limit=10, offset=0)
    assert len(page.items) == 1
    assert page.items[0].solve_id == solved.solve_id

    stored = get_solve(solved.solve_id)
    assert stored.answer == solved.answer


def test_export_markdown_route_returns_stored_solve_artifact() -> None:
    solved = solve_question(SolveRequestBody(question="求 x^2 对 x 的导数"))

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
    solved = solve_question(SolveRequestBody(question="求 x^2 对 x 的导数"))

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
    assert "solveQuestion" in script
    assert "renderLatex" in script
    assert "renderMathText" in script
    assert "refreshLlmStatus" in script
    assert "/llm/status" in script
    assert "Gemma: 已连接" in script
    assert "Gemma: 未连接" in script
    assert "window.katex" in script
    assert "编辑 LaTeX" in script
    assert "data-copy-formula" in script
    assert "copyText" in script
    assert "noteMarkdown" in script
    assert "markdownArtifact" in script
    assert "/export.md" in script
    assert "downloadText" in script
    assert "resizeComposer" in script
