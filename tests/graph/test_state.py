from examsolver.graph.state import SolveState


def test_solve_state_declares_architecture_fields() -> None:
    expected = {
        "request_id",
        "raw_question",
        "image_paths",
        "user_subject_hint",
        "ocr_text",
        "ocr_bboxes",
        "vision_description",
        "needs_vision",
        "normalized",
        "subject",
        "question_type",
        "routing_confidence",
        "routing_reasoning",
        "retrieved_chunks",
        "solve_result",
        "note",
        "response",
        "errors",
        "fallback_reasons",
    }

    assert expected <= set(SolveState.__annotations__)
