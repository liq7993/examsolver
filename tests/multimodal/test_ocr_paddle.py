from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from examsolver.multimodal import OCRError
from examsolver.multimodal import ocr_paddle
from examsolver.multimodal.ocr_paddle import OCRResult, PaddleOCREngine

FIXTURE = Path(__file__).parents[1] / "fixtures" / "ocr" / "sample_zh.png"
HANDWRITTEN_FIXTURE = Path(__file__).parents[1] / "fixtures" / "ocr" / "handwritten_formula.png"


class FakePaddleOCR:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def ocr(self, image_path: str) -> list[list[Any]]:
        self.calls.append(image_path)
        return [
            [
                [[[10, 10], [240, 10], [240, 50], [10, 50]], ("题目：求 x^2 的导数", 0.98)],
                [[[10, 70], [240, 70], [240, 110], [10, 110]], ("公式：d/dx x^2 = 2x", 0.92)],
            ]
        ]


def test_ocr_result_is_serializable_contract() -> None:
    result = OCRResult(text="题目", bboxes=[{"bbox": [[0, 0]], "confidence": 0.9}], confidence=0.9)

    assert result.text == "题目"
    assert result.bboxes[0]["bbox"] == [[0, 0]]
    assert result.confidence == 0.9


def test_engine_parses_paddleocr_output_without_numpy() -> None:
    fake = FakePaddleOCR()
    engine = PaddleOCREngine(paddle_ocr=fake)

    result = engine.recognize([FIXTURE])

    assert "题目" in result.text
    assert "公式" in result.text
    assert result.confidence == pytest.approx(0.95)
    assert result.bboxes == [
        {
            "text": "题目：求 x^2 的导数",
            "bbox": [[10, 10], [240, 10], [240, 50], [10, 50]],
            "confidence": 0.98,
            "source": str(FIXTURE),
        },
        {
            "text": "公式：d/dx x^2 = 2x",
            "bbox": [[10, 70], [240, 70], [240, 110], [10, 110]],
            "confidence": 0.92,
            "source": str(FIXTURE),
        },
    ]


def test_engine_supports_paddleocr_v3_dict_output() -> None:
    class FakeV3:
        def ocr(self, image_path: str) -> list[dict[str, Any]]:
            return [
                {
                    "rec_texts": ["中文", "x^2"],
                    "rec_scores": [0.8, 0.6],
                    "rec_polys": [
                        [[1, 2], [3, 4]],
                        [[5, 6], [7, 8]],
                    ],
                }
            ]

    result = PaddleOCREngine(paddle_ocr=FakeV3()).recognize([FIXTURE])

    assert result.text == "中文\nx^2"
    assert result.confidence == pytest.approx(0.7)


def test_missing_image_raises_ocr_error() -> None:
    engine = PaddleOCREngine(paddle_ocr=FakePaddleOCR())

    with pytest.raises(OCRError, match="does not exist"):
        engine.recognize([Path("missing.png")])


def test_singleton_is_lazy(monkeypatch: pytest.MonkeyPatch) -> None:
    ocr_paddle._reset_for_tests()
    constructed = 0

    class LazyFake:
        def __init__(self, **kwargs: object) -> None:
            nonlocal constructed
            constructed += 1
            assert kwargs["use_doc_orientation_classify"] is False
            assert kwargs["use_doc_unwarping"] is False
            assert kwargs["use_textline_orientation"] is False
            assert kwargs["device"] == "cpu"
            assert kwargs["engine"] == "paddle_static"
            assert kwargs["enable_mkldnn"] is False
            assert kwargs["engine_config"] == {
                "paddle_static": {
                    "run_mode": "paddle",
                    "enable_new_ir": False,
                    "enable_cinn": False,
                    "cpu_threads": 1,
                },
            }

        def ocr(self, image_path: str) -> list[list[Any]]:
            return [[[[[0, 0], [1, 0], [1, 1], [0, 1]], ("lazy", 1.0)]]]

    fake_module = ModuleType("paddleocr")
    setattr(fake_module, "PaddleOCR", LazyFake)
    monkeypatch.setitem(sys.modules, "paddleocr", fake_module)

    engine = ocr_paddle.get_engine()
    assert constructed == 0

    result = engine.recognize([FIXTURE])

    assert result.text == "lazy"
    assert constructed == 1
    assert ocr_paddle.get_engine() is engine
    ocr_paddle._reset_for_tests()


@pytest.mark.slow
@pytest.mark.skipif(
    not os.getenv("EXAMSOLVER_RUN_SLOW_OCR"),
    reason="real PaddleOCR timing test is opt-in to avoid model downloads in normal CI",
)
def test_real_paddleocr_processes_1024x768_under_three_seconds_after_warmup() -> None:
    engine = ocr_paddle.get_engine()
    engine.recognize([HANDWRITTEN_FIXTURE])

    started = time.perf_counter()
    result = engine.recognize([HANDWRITTEN_FIXTURE])
    elapsed = time.perf_counter() - started

    assert elapsed < 3.0
    assert result.text
