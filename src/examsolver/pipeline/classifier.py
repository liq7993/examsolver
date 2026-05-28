"""Rule-based question classification layer."""

from __future__ import annotations

import re
from collections.abc import Callable

from examsolver.contracts import NormalizedQuestion

Rule = tuple[str, Callable[[str], bool]]
_FORCE_QUANTITY_PATTERN = re.compile(r"[-+]?\d+(?:\.\d+)?\s*(?:kn|n|牛顿)\b", re.IGNORECASE)


def classify(question: NormalizedQuestion) -> str:
    """Return a deterministic question_type for the normalized question."""

    text = _without_latex_noise(question.normalized_text).lower()
    rules: list[Rule] = [
        ("derivative", _looks_like_derivative),
        ("matrix_mul", _looks_like_matrix_multiplication),
        ("force_balance", _looks_like_force_balance),
        ("fit_type", _looks_like_fit_type),
    ]
    for question_type, predicate in rules:
        if predicate(text):
            return question_type
    return "unknown"


def _looks_like_derivative(text: str) -> bool:
    return any(keyword in text for keyword in ("导数", "求导", "derivative", "d/dx", "frac{d}{dx}"))


def _looks_like_matrix_multiplication(text: str) -> bool:
    return ("矩阵" in text and "乘" in text) or ("matrix" in text and ("mul" in text or "*" in text))


def _looks_like_force_balance(text: str) -> bool:
    has_force_quantity = _FORCE_QUANTITY_PATTERN.search(text) is not None
    has_force_word = any(keyword in text for keyword in ("力", "force", "forces"))
    has_intent = any(
        keyword in text
        for keyword in (
            "平衡",
            "分解",
            "分力",
            "合力",
            "equilibrium",
            "equilibrant",
            "balance",
            "balanced",
            "opposite",
            "component",
            "components",
            "resolve",
        )
    )
    return has_force_quantity and has_intent and (has_force_word or "平衡" in text)


def _looks_like_fit_type(text: str) -> bool:
    has_fit_pair = re.search(r"\b[a-z]\s*\d{1,2}\s*[/／-]\s*[a-z]\s*\d{1,2}\b", text) is not None
    has_tolerance_word = any(keyword in text for keyword in ("配合", "公差", "基本偏差", "fit", "tolerance"))
    asks_hole_shaft_symbol = "孔" in text and "轴" in text and "代号" in text
    has_symbol = re.search(r"\b[A-Za-z]\s*\d{1,2}\b", text) is not None
    return has_fit_pair or (has_tolerance_word and has_symbol) or asks_hole_shaft_symbol


def _without_latex_noise(text: str) -> str:
    return text.replace("$", "").replace("\\", "")
