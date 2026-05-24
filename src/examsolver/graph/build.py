"""Build and execute the LangGraph solve graph."""

from __future__ import annotations

import logging
from functools import cache
from typing import cast

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from examsolver.contracts import ExplanationEnhancer, SolveRequest, SolveResponse
from examsolver.graph.nodes import (
    explanation_enhancer_node,
    format_node,
    normalize_node,
    note_builder_node,
    persist_node,
    router_agent_node,
    skill_node,
)
from examsolver.graph.state import SolveGraphState
from examsolver.pipeline.formatter import format_response
from examsolver.pipeline.normalizer import normalize
from examsolver.services.explanation import build_default_enhancer
from examsolver.skills.base import NormalizationError
from examsolver.skills.unknown_skill import UnknownSkill

logger = logging.getLogger(__name__)


@cache
def build_graph() -> CompiledStateGraph:
    """Compile the M1 solve graph."""

    graph = StateGraph(SolveGraphState)
    graph.add_node("normalize", normalize_node)
    graph.add_node("router_agent", router_agent_node)
    graph.add_node("skill", skill_node)
    graph.add_node("explanation_enhancer", explanation_enhancer_node)
    graph.add_node("note_builder", note_builder_node)
    graph.add_node("format", format_node)
    graph.add_node("persist", persist_node)

    graph.add_edge(START, "normalize")
    graph.add_edge("normalize", "router_agent")
    graph.add_edge("router_agent", "skill")
    graph.add_edge("skill", "explanation_enhancer")
    graph.add_edge("explanation_enhancer", "note_builder")
    graph.add_edge("note_builder", "format")
    graph.add_edge("format", "persist")
    graph.add_edge("persist", END)
    return graph.compile()


def run_solve_graph(
    request: SolveRequest,
    *,
    enhancer: ExplanationEnhancer | None = None,
) -> SolveResponse:
    """Run one request through the compiled graph."""

    try:
        selected_enhancer = enhancer or build_default_enhancer()
        output = cast(
            SolveGraphState,
            build_graph().invoke({"request": request, "enhancer": selected_enhancer}),
        )
    except NormalizationError:
        fallback = normalize(SolveRequest(question="unsupported"))
        result = UnknownSkill().solve(fallback)
        return format_response(fallback, result)

    response = output["response"]
    logger.info("[%s] solve graph done success=%s", response.solve_id, response.success)
    return response
