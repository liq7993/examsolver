"""Input normalization layer."""

from __future__ import annotations

import re
import unicodedata
import uuid
from datetime import UTC, datetime

from examsolver.contracts import NormalizedQuestion, SolveRequest
from examsolver.skills.base import NormalizationError

_LATEX_SEGMENT_PATTERN = re.compile(r"(?<!\\)\$\$?.+?(?<!\\)\$\$?", re.DOTALL)
_FORCE_QUANTITY_PATTERN = re.compile(r"[-+]?\d+(?:\.\d+)?\s*(?:kn|n|牛顿)\b", re.IGNORECASE)


def normalize(request: SolveRequest) -> NormalizedQuestion:
    """Normalize a raw solve request without classifying it."""

    raw_text = request.question
    if not isinstance(raw_text, str) or not raw_text.strip():
        raise NormalizationError("question must be a non-empty string")

    normalized_text = unicodedata.normalize("NFKC", raw_text).strip()
    latex_segments = len(_LATEX_SEGMENT_PATTERN.findall(normalized_text))
    subject = request.subject_hint or request.subject or _infer_subject(normalized_text)
    image_paths = list(request.image_paths)

    return NormalizedQuestion(
        raw_text=raw_text,
        normalized_text=normalized_text,
        subject=subject,
        has_image=bool(image_paths),
        image_paths=image_paths,
        ocr_text="",
        vision_description="",
        hints={
            "request_id": uuid.uuid4().hex,
            "solve_id": uuid.uuid4().hex,
            "created_at": datetime.now(UTC).isoformat(),
            "has_latex": latex_segments > 0,
            "latex_segments": latex_segments,
            "image_count": len(image_paths),
        },
    )


def _infer_subject(text: str) -> str:
    lowered = text.lower()
    if any(keyword in lowered for keyword in ("导数", "求导", "derivative", "d/dx", "\\frac{d}{dx}")):
        return "calculus"
    if any(keyword in lowered for keyword in ("矩阵", "matrix")):
        return "linear_algebra"
    if any(keyword in lowered for keyword in ("配合", "公差", "基本偏差", "h7", "g6", "tolerance", "fit")):
        return "tolerance"
    if any(
        keyword in lowered
        for keyword in (
            "平衡力",
            "平衡",
            "分力",
            "分解",
            "合力",
            "力",
            "force",
            "forces",
            "equilibrium",
            "equilibrant",
            "component",
        )
    ) or (_FORCE_QUANTITY_PATTERN.search(text) is not None and "平衡" in lowered):
        return "mechanics"
    return "unknown"
