"""PaddleOCR adapter with lazy singleton model loading."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any, cast

from examsolver.multimodal import OCRError


@dataclass(frozen=True, slots=True)
class OCRResult:
    """Serializable OCR output for LangGraph state."""

    text: str
    bboxes: list[dict[str, Any]]
    confidence: float


class PaddleOCREngine:
    """Thin synchronous wrapper around PaddleOCR."""

    def __init__(self, paddle_ocr: Any | None = None) -> None:
        self._paddle_ocr = paddle_ocr

    def recognize(self, image_paths: list[str | Path]) -> OCRResult:
        """Run OCR over one or more image paths and merge the text blocks."""

        if not image_paths:
            raise OCRError("at least one image path is required")

        texts: list[str] = []
        bboxes: list[dict[str, Any]] = []
        confidences: list[float] = []
        ocr = self._load()
        for image_path in image_paths:
            path = Path(image_path)
            if not path.exists():
                raise OCRError(f"OCR image does not exist: {path}")
            try:
                raw = _run_ocr(ocr, path)
            except Exception as exc:
                raise OCRError(f"OCR failed for {path}") from exc
            blocks = _parse_blocks(raw, source=str(path))
            for block in blocks:
                text = str(block["text"])
                if text:
                    texts.append(text)
                confidences.append(float(block["confidence"]))
                bboxes.append(block)

        confidence = sum(confidences) / len(confidences) if confidences else 0.0
        return OCRResult(text="\n".join(texts), bboxes=bboxes, confidence=confidence)

    def _load(self) -> Any:
        if self._paddle_ocr is None:
            try:
                from paddleocr import PaddleOCR  # type: ignore[import-untyped]
            except Exception as exc:
                raise OCRError("PaddleOCR is not importable") from exc
            try:
                self._paddle_ocr = PaddleOCR(use_angle_cls=True, lang="ch")
            except Exception as exc:
                raise OCRError("PaddleOCR model initialization failed") from exc
        return self._paddle_ocr


_ENGINE: PaddleOCREngine | None = None
_ENGINE_LOCK = Lock()


def get_engine() -> PaddleOCREngine:
    """Return the process-wide lazy OCR engine singleton."""

    global _ENGINE
    if _ENGINE is None:
        with _ENGINE_LOCK:
            if _ENGINE is None:
                _ENGINE = PaddleOCREngine()
    return _ENGINE


def recognize(image_paths: list[str | Path]) -> OCRResult:
    """Convenience function using the singleton engine."""

    return get_engine().recognize(image_paths)


def _reset_for_tests() -> None:
    """Reset the singleton so tests can assert lazy loading behavior."""

    global _ENGINE
    with _ENGINE_LOCK:
        _ENGINE = None


def _run_ocr(ocr: Any, path: Path) -> Any:
    if hasattr(ocr, "ocr"):
        return ocr.ocr(str(path))
    if hasattr(ocr, "predict"):
        return ocr.predict(str(path))
    raise OCRError("PaddleOCR instance has neither ocr nor predict")


def _parse_blocks(raw: Any, *, source: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for page in _pages(raw):
        if isinstance(page, dict):
            blocks.extend(_parse_dict_page(page, source=source))
            continue
        for item in _items(page):
            parsed = _parse_item(item, source=source)
            if parsed is not None:
                blocks.append(parsed)
    return blocks


def _pages(raw: Any) -> list[Any]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    return [raw]


def _items(page: Any) -> list[Any]:
    if page is None:
        return []
    if isinstance(page, list):
        return page
    return [page]


def _parse_dict_page(page: dict[str, Any], *, source: str) -> list[dict[str, Any]]:
    texts = page.get("rec_texts") or page.get("texts") or []
    scores = page.get("rec_scores") or page.get("scores") or []
    boxes = page.get("rec_polys") or page.get("rec_boxes") or page.get("dt_polys") or []
    if not isinstance(texts, list):
        return []

    blocks: list[dict[str, Any]] = []
    for index, text in enumerate(texts):
        confidence = _float_at(scores, index, default=0.0)
        box = _value_at(boxes, index)
        blocks.append(_block(text=str(text), confidence=confidence, box=box, source=source))
    return blocks


def _parse_item(item: Any, *, source: str) -> dict[str, Any] | None:
    if not isinstance(item, list | tuple) or len(item) < 2:
        return None

    box = item[0]
    text_part = item[1]
    if isinstance(text_part, list | tuple) and len(text_part) >= 2:
        text = str(text_part[0])
        confidence = _to_float(text_part[1], default=0.0)
        return _block(text=text, confidence=confidence, box=box, source=source)
    if isinstance(text_part, str):
        confidence = _to_float(item[2], default=0.0) if len(item) >= 3 else 0.0
        return _block(text=text_part, confidence=confidence, box=box, source=source)
    return None


def _block(*, text: str, confidence: float, box: Any, source: str) -> dict[str, Any]:
    return {
        "text": text,
        "bbox": _jsonable_box(box),
        "confidence": confidence,
        "source": source,
    }


def _jsonable_box(box: Any) -> list[Any]:
    if hasattr(box, "tolist"):
        value = box.tolist()
    else:
        value = box
    return cast(list[Any], _jsonable(value))


def _jsonable(value: Any) -> Any:
    if isinstance(value, list | tuple):
        return [_jsonable(item) for item in value]
    if hasattr(value, "item"):
        return value.item()
    return value


def _value_at(values: Any, index: int) -> Any:
    if isinstance(values, list | tuple) and index < len(values):
        return values[index]
    return []


def _float_at(values: Any, index: int, *, default: float) -> float:
    return _to_float(_value_at(values, index), default=default)


def _to_float(value: Any, *, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
