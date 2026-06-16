"""FastAPI application shell."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from examsolver.api.routes.capabilities import router as capabilities_router
from examsolver.api.routes.export import router as export_router
from examsolver.api.routes.health import router as health_router
from examsolver.api.routes.library import router as library_router
from examsolver.api.routes.llm import router as llm_router
from examsolver.api.routes.solve import router as solve_router

STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_app() -> FastAPI:
    """Create the FastAPI app without embedding solve business logic."""

    app = FastAPI(title="Examsolver", version="0.0.1")
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^http://(localhost|127\.0\.0\.1):\d+$",
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(capabilities_router)
    app.include_router(llm_router)
    app.include_router(library_router)
    app.include_router(solve_router)
    app.include_router(export_router)

    @app.get("/", include_in_schema=False, name="frontend_index")
    def frontend_index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.head("/", include_in_schema=False, name="frontend_head")
    def frontend_head() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="frontend_static")
    return app


app = create_app()
