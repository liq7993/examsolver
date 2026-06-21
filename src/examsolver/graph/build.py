"""Build and execute the LangGraph solve graph."""

from __future__ import annotations

import logging
from functools import cache
from typing import Any, cast

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from examsolver.contracts import ExplanationEnhancer, SolveRequest, SolveResponse
from examsolver.graph.nodes import (
    explanation_enhancer_node,
    format_node,
    general_node,
    has_images,
    normalize_node,
    note_builder_node,
    ocr_node,
    persist_node,
    plot_node,
    rag_retrieve_node,
    route_after_rag,
    route_after_router_agent,
    route_after_vlm,
    router_agent_node,
    skill_node,
    vlm_node,
)
from examsolver.graph.state import SolveGraphState
from examsolver.pipeline.formatter import format_response
from examsolver.pipeline.normalizer import normalize
from examsolver.services.explanation import build_default_enhancer
from examsolver.skills.base import NormalizationError
from examsolver.skills.unknown_skill import UnknownSkill

logger = logging.getLogger(__name__)


@cache
def build_graph() -> CompiledStateGraph[Any, Any, Any, Any]:
    """Compile the M1 solve graph."""

    graph = StateGraph(SolveGraphState)
    graph.add_node("normalize", normalize_node)
    graph.add_node("ocr", ocr_node)
    graph.add_node("vlm", vlm_node)
    graph.add_node("router_agent", router_agent_node)
    graph.add_node("rag_retrieve", rag_retrieve_node)
    graph.add_node("skill", skill_node)
    graph.add_node("general", general_node)
    graph.add_node("explanation_enhancer", explanation_enhancer_node)
    graph.add_node("plot", plot_node)
    graph.add_node("note_builder", note_builder_node)
    graph.add_node("format", format_node)
    graph.add_node("persist", persist_node)

    graph.add_edge(START, "normalize")
    graph.add_conditional_edges(
        "normalize",
        has_images,
        {"ocr": "ocr", "router_agent": "router_agent"},
    )
    graph.add_edge("ocr", "router_agent")
    graph.add_conditional_edges(
        "router_agent",
        route_after_router_agent,
        {"vlm": "vlm", "rag_retrieve": "rag_retrieve", "skill": "skill", "general": "general"},
    )
    graph.add_conditional_edges(
        "vlm",
        route_after_vlm,
        {"rag_retrieve": "rag_retrieve", "skill": "skill", "general": "general"},
    )
    graph.add_conditional_edges(
        "rag_retrieve",
        route_after_rag,
        {"skill": "skill", "general": "general"},
    )
    graph.add_edge("skill", "explanation_enhancer")
    graph.add_edge("general", "explanation_enhancer")
    graph.add_edge("explanation_enhancer", "plot")
    graph.add_edge("plot", "note_builder")
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
    request_id = str(output["normalized"].hints.get("request_id", "unknown"))
    logger.info(
        "[%s] INFO graph.build.run_solve_graph: done success=%s",
        request_id,
        response.success,
    )
    return response
