"""Solve service orchestration layer."""

from __future__ import annotations

from examsolver.contracts import ExplanationEnhancer, SolveRequest, SolveResponse
from examsolver.graph import run_solve_graph


def solve(
    request: SolveRequest,
    *,
    enhancer: ExplanationEnhancer | None = None,
) -> SolveResponse:
    """Run the LangGraph-backed solve orchestration for one question."""

    return run_solve_graph(request, enhancer=enhancer)
