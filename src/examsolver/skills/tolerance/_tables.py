"""Small ISO 286-style basic deviation lookup table for common fit symbols."""

from __future__ import annotations

import re
from dataclasses import dataclass

_SYMBOL_PATTERN = re.compile(r"^(?P<letter>[A-Za-z]+)(?P<grade>\d+)?$")


@dataclass(frozen=True, slots=True)
class BasicDeviation:
    """Simplified tolerance-zone interval in micrometres."""

    symbol: str
    component: str
    letter: str
    grade: int
    lower_um: int
    upper_um: int


_IT_GRADES_UM = {
    5: 8,
    6: 13,
    7: 21,
    8: 33,
    9: 52,
}

# Simplified, representative zones for common teaching examples around nominal sizes.
_HOLE_LOWER_UM = {
    "G": -7,
    "H": 0,
    "K": -9,
}
_SHAFT_UPPER_UM = {
    "g": -7,
    "h": 0,
    "k": 9,
}


def lookup_basic_deviation(symbol: str, component: str) -> BasicDeviation:
    """Return a simplified basic deviation interval for a hole or shaft symbol."""

    normalized_component = component.strip().lower()
    if normalized_component not in {"hole", "shaft"}:
        raise ValueError("component must be 'hole' or 'shaft'")

    letter, grade = _parse_symbol(symbol)
    width = _IT_GRADES_UM.get(grade, _IT_GRADES_UM[7])
    if normalized_component == "hole":
        lower = _lookup_hole_lower(letter)
        return BasicDeviation(
            symbol=f"{letter.upper()}{grade}",
            component="hole",
            letter=letter.upper(),
            grade=grade,
            lower_um=lower,
            upper_um=lower + width,
        )

    upper = _lookup_shaft_upper(letter)
    return BasicDeviation(
        symbol=f"{letter.lower()}{grade}",
        component="shaft",
        letter=letter.lower(),
        grade=grade,
        lower_um=upper - width,
        upper_um=upper,
    )


def judge_fit_type(hole: BasicDeviation, shaft: BasicDeviation) -> str:
    """Classify fit type from hole and shaft tolerance intervals."""

    min_clearance = hole.lower_um - shaft.upper_um
    max_clearance = hole.upper_um - shaft.lower_um
    if min_clearance >= 0:
        return "间隙"
    if max_clearance <= 0:
        return "过盈"
    return "过渡"


def _parse_symbol(symbol: str) -> tuple[str, int]:
    compact = symbol.strip()
    match = _SYMBOL_PATTERN.match(compact)
    if match is None:
        raise ValueError(f"invalid tolerance symbol: {symbol}")
    letter = match.group("letter")
    grade_text = match.group("grade")
    grade = int(grade_text) if grade_text else 7
    return letter, grade


def _lookup_hole_lower(letter: str) -> int:
    key = letter.upper()
    if key not in _HOLE_LOWER_UM:
        raise ValueError(f"unsupported hole basic deviation: {letter}")
    return _HOLE_LOWER_UM[key]


def _lookup_shaft_upper(letter: str) -> int:
    key = letter.lower()
    if key not in _SHAFT_UPPER_UM:
        raise ValueError(f"unsupported shaft basic deviation: {letter}")
    return _SHAFT_UPPER_UM[key]
