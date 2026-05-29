import pytest

from examsolver.contracts import NormalizedQuestion
from examsolver.graph.nodes import general_node, rag_retrieve_node, route_after_router, skill_node
from examsolver.rag.retriever import TextbookChunk


def test_skill_node_writes_solve_result_for_known_skill() -> None:
    state = skill_node(
        {
            "normalized": NormalizedQuestion(
                raw_text="求 x^2 对 x 的导数",
                normalized_text="求 x^2 对 x 的导数",
                subject="calculus",
                hints={"request_id": "rid-1"},
            ),
            "question_type": "derivative",
        }
    )

    assert state["solve_result"].skill == "calculus.derivative"


def test_route_after_router_sends_rag_backed_skill_to_retrieval() -> None:
    assert (
        route_after_router(
            {
                "normalized": NormalizedQuestion(
                    raw_text="H7/g6 是什么配合？",
                    normalized_text="H7/g6 是什么配合？",
                    subject="tolerance",
                ),
                "subject": "tolerance",
                "question_type": "fit_type",
            }
        )
        == "rag_retrieve"
    )


def test_rag_retrieve_node_writes_chunks_for_textbook_subject(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []
    chunk = _chunk()

    def fake_retrieve(*, query: str, subject: str) -> list[TextbookChunk]:
        calls.append((query, subject))
        return [chunk]

    monkeypatch.setattr("examsolver.graph.nodes.rag_retriever.retrieve", fake_retrieve)

    state = rag_retrieve_node(
        {
            "normalized": NormalizedQuestion(
                raw_text="H7/g6 是什么配合？",
                normalized_text="H7/g6 是什么配合？",
                subject="tolerance",
                hints={"request_id": "rid-1"},
            ),
            "subject": "tolerance",
            "question_type": "fit_type",
        }
    )

    assert calls == [("H7/g6 是什么配合？", "tolerance")]
    assert state["retrieved_chunks"] == [chunk]


def test_skill_node_injects_pre_retrieved_chunks() -> None:
    state = skill_node(
        {
            "normalized": NormalizedQuestion(
                raw_text="H7/g6 是什么配合？",
                normalized_text="H7/g6 是什么配合？",
                subject="tolerance",
                hints={"request_id": "rid-1"},
            ),
            "subject": "tolerance",
            "question_type": "fit_type",
            "retrieved_chunks": [_chunk()],
        }
    )

    result = state["solve_result"]
    assert result.skill == "tolerance.fit_type"
    assert result.citations[0].chunk_id == "chunk-h7"


def test_general_node_writes_general_cot_result() -> None:
    state = general_node(
        {
            "normalized": NormalizedQuestion(
                raw_text="汽车 ABS 起到什么作用？",
                normalized_text="汽车 ABS 起到什么作用？",
                subject="unknown",
                hints={"request_id": "rid-1"},
            )
        }
    )

    assert state["solve_result"].skill == "general.cot_with_textbook"
    assert state["solve_result"].answer is not None
    assert state["solve_result"].meta["common_mistakes"]


def _chunk() -> TextbookChunk:
    return TextbookChunk(
        id="chunk-h7",
        document_id="doc-tolerance",
        document_title="公差",
        subject="tolerance",
        page=1,
        text="H7/g6 常用于说明孔轴配合。",
        score=0.1,
    )


def test_general_node_falls_back_to_unknown_on_general_skill_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("examsolver.graph.nodes.pick_llm", lambda *_args, **_kwargs: None)

    state = general_node(
        {
            "normalized": NormalizedQuestion(
                raw_text="解释天气",
                normalized_text="解释天气",
                subject="unknown",
                hints={"request_id": "rid-1"},
            )
        }
    )

    assert state["solve_result"].skill == "unknown"
    assert state["fallback_reasons"] == ["general_skill_failed"]


def test_skill_node_records_fallback_reason_on_skill_failure() -> None:
    state = skill_node(
        {
            "normalized": NormalizedQuestion(
                raw_text="计算矩阵 [[1,2]] 乘 [[1,2]]",
                normalized_text="计算矩阵 [[1,2]] 乘 [[1,2]]",
                subject="linear_algebra",
                hints={"request_id": "rid-1"},
            ),
            "question_type": "matrix_mul",
        }
    )

    assert state["solve_result"].skill == "unknown"
    assert state["fallback_reasons"] == ["primary_skill_failed"]
