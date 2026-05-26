from __future__ import annotations

import pytest

from examsolver.contracts import NormalizedQuestion
from examsolver.graph.nodes import has_images, ocr_node
from examsolver.multimodal import OCRError
from examsolver.multimodal.ocr_paddle import OCRResult


def test_ocr_node_runs_when_images_are_present(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_recognize(image_paths: list[str]) -> OCRResult:
        calls.append(image_paths)
        return OCRResult(
            text="中文题目\nE=mc^2",
            bboxes=[
                {
                    "text": "中文题目",
                    "bbox": [[0, 0], [10, 0], [10, 10], [0, 10]],
                    "confidence": 0.95,
                    "source": "tests/fixtures/ocr/sample_zh.png",
                }
            ],
            confidence=0.95,
        )

    monkeypatch.setattr("examsolver.graph.nodes.recognize", fake_recognize)
    normalized = _normalized(image_paths=["tests/fixtures/ocr/sample_zh.png"])

    state = ocr_node({"normalized": normalized})

    assert calls == [["tests/fixtures/ocr/sample_zh.png"]]
    assert state["ocr_text"] == "中文题目\nE=mc^2"
    assert state["ocr_bboxes"][0]["text"] == "中文题目"
    assert "image_bytes" not in state


def test_ocr_node_skips_when_no_images(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_recognize(_image_paths: list[str]) -> OCRResult:
        raise AssertionError("OCR should not be called for text-only requests")

    monkeypatch.setattr("examsolver.graph.nodes.recognize", fail_recognize)
    normalized = _normalized(image_paths=[])

    assert has_images({"normalized": normalized}) == "router_agent"
    assert ocr_node({"normalized": normalized}) == {}


def test_ocr_node_appends_fallback_reason_when_ocr_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_recognize(_image_paths: list[str]) -> OCRResult:
        raise OCRError("sample failure")

    monkeypatch.setattr("examsolver.graph.nodes.recognize", fail_recognize)
    normalized = _normalized(image_paths=["missing.png"])

    state = ocr_node({"normalized": normalized, "fallback_reasons": ["previous"]})

    assert has_images({"normalized": normalized}) == "ocr"
    assert state["fallback_reasons"] == ["previous", "ocr_failed:sample failure"]
    assert "ocr_text" not in state
    assert "ocr_bboxes" not in state


def _normalized(*, image_paths: list[str]) -> NormalizedQuestion:
    return NormalizedQuestion(
        raw_text="看这张图里是什么",
        normalized_text="看这张图里是什么",
        subject="unknown",
        has_image=bool(image_paths),
        image_paths=image_paths,
        hints={"request_id": "rid-ocr"},
    )
