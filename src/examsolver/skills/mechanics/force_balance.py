"""Deterministic mechanics force balance skill."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Literal

from examsolver.contracts import NormalizedQuestion, SolveResult, Step, StudentExplanation

Intent = Literal["find_balanced_force", "find_components", "check_equilibrium"]


@dataclass(frozen=True, slots=True)
class Force:
    magnitude: float
    unit: str
    angle_deg: float
    label: str


@dataclass(frozen=True, slots=True)
class Components:
    x: float
    y: float


_FORCE_QUANTITY_RE = re.compile(
    r"(?P<magnitude>[-+]?\d+(?:\.\d+)?)\s*(?P<unit>kn|n|牛顿)\b",
    re.IGNORECASE,
)
_ANGLE_RE = re.compile(r"([-+]?\d+(?:\.\d+)?)\s*(?:°|度|deg(?:ree)?s?)", re.IGNORECASE)
_BARE_ANGLE_RE = re.compile(
    r"(?:成|at)\s*([-+]?\d+(?:\.\d+)?)(?=\s*(?:,|，|。|\.|into|to|from|with|的|力|$))",
    re.IGNORECASE,
)
_DIRECTION_ANGLES: tuple[tuple[str, float, str], ...] = (
    ("向右", 0.0, "向右"),
    ("right", 0.0, "向右"),
    ("east", 0.0, "向右"),
    ("向上", 90.0, "向上"),
    ("upward", 90.0, "向上"),
    ("up", 90.0, "向上"),
    ("north", 90.0, "向上"),
    ("向左", 180.0, "向左"),
    ("left", 180.0, "向左"),
    ("west", 180.0, "向左"),
    ("向下", 270.0, "向下"),
    ("downward", 270.0, "向下"),
    ("down", 270.0, "向下"),
    ("south", 270.0, "向下"),
)
_EXPLANATION_TEMPLATES: dict[Intent, dict[str, str]] = {
    "find_balanced_force": {
        "summary": "平衡力的大小与已知力相等，方向与已知力相反。",
        "intuition": "平衡力的本质，是把已知力完整抵消掉，让合力重新回到零。",
        "common_mistake": "不要把平衡力写成同向叠加，只需要保持大小不变并把方向反过来。",
        "self_check_question": "把已知力和你求出的力相加后，合力是否为零？",
    },
    "find_components": {
        "summary": "分解力时，要把一个斜向力拆成互相垂直的 x、y 两个分量。",
        "intuition": "一个斜着的力，可以看成一个水平作用和一个竖直作用共同叠加出来的结果。",
        "common_mistake": "不要把整个力直接抄到某个坐标轴上，要分别计算两个分量，并保留正确正负号。",
        "self_check_question": "把 Fx 和 Fy 重新合成后，是否能恢复原来的大小和方向？",
    },
    "check_equilibrium": {
        "summary": "只有当 x 方向合力和 y 方向合力都等于零时，系统才处于平衡。",
        "intuition": '平衡不是"看起来差不多"，而是每个方向上的作用都被完全抵消。',
        "common_mistake": "不能只比较力的大小，还要检查各方向分量相加后是否都归零。",
        "self_check_question": "把所有力沿 x、y 方向分别求和后，结果各是多少？",
    },
}


class ForceBalanceSkill:
    """Solve a small deterministic subset of force balance questions."""

    name = "mechanics.force_balance"
    version = "0.1.0"
    subject = "mechanics"
    question_types = ["force_balance"]

    def can_handle(self, question: NormalizedQuestion) -> bool:
        text = question.normalized_text.lower()
        return _has_force_quantity(text) and any(keyword in text for keyword in ("力", "force"))

    def solve(self, question: NormalizedQuestion) -> SolveResult:
        text = question.normalized_text
        intent = _detect_intent(text)
        if intent == "find_components":
            return _solve_components(text, self.name, self.version)
        if intent == "check_equilibrium":
            return _solve_equilibrium(text, self.name, self.version)
        return _solve_balanced_force(text, self.name, self.version)


def _solve_balanced_force(text: str, skill_name: str, skill_version: str) -> SolveResult:
    force = _single_force(text)
    opposite_angle = _normalize_angle(force.angle_deg + 180.0)
    opposite_label = _direction_label(opposite_angle)
    answer = f"${_format_number(force.magnitude)}\\,\\mathrm{{{force.unit}}}$，方向{opposite_label}"
    steps = [
        Step(
            index=1,
            description=f"识别已知力方向{force.label}",
            formula_latex=rf"F={_format_number(force.magnitude)}\,\mathrm{{{force.unit}}}",
        ),
        Step(
            index=2,
            description="平衡力需要让合力为零，因此大小相等、方向相反",
            formula_latex=r"\vec F+\vec F_{\mathrm{bal}}=\vec 0",
        ),
        Step(
            index=3,
            description=f"把方向旋转 180 度，得到平衡力方向{opposite_label}",
            formula_latex=rf"\theta_{{\mathrm{{bal}}}}={_format_number(opposite_angle)}^\circ",
        ),
    ]
    return _result(
        intent="find_balanced_force",
        skill_name=skill_name,
        skill_version=skill_version,
        steps=steps,
        answer=answer,
        meta={
            "mechanics.force_balance.intent": "find_balanced_force",
            "mechanics.force_balance.force_count": 1,
            "mechanics.force_balance.angle_deg": force.angle_deg,
            "mechanics.force_balance.balanced_angle_deg": opposite_angle,
        },
    )


def _solve_components(text: str, skill_name: str, skill_version: str) -> SolveResult:
    force = _single_force(text)
    components = _components(force)
    answer = {
        "Fx": f"${_format_number(components.x)}\\,\\mathrm{{{force.unit}}}$",
        "Fy": f"${_format_number(components.y)}\\,\\mathrm{{{force.unit}}}$",
    }
    steps = [
        Step(
            index=1,
            description="识别力的大小和与 x 轴夹角",
            formula_latex=(
                rf"F={_format_number(force.magnitude)}\,\mathrm{{{force.unit}}},"
                rf"\quad \theta={_format_number(force.angle_deg)}^\circ"
            ),
        ),
        Step(
            index=2,
            description="沿 x、y 方向分解",
            formula_latex=r"F_x=F\cos\theta,\quad F_y=F\sin\theta",
        ),
        Step(
            index=3,
            description="代入得到两个分量",
            formula_latex=(
                rf"F_x={_format_number(components.x)}\,\mathrm{{{force.unit}}},"
                rf"\quad F_y={_format_number(components.y)}\,\mathrm{{{force.unit}}}"
            ),
        ),
    ]
    return _result(
        intent="find_components",
        skill_name=skill_name,
        skill_version=skill_version,
        steps=steps,
        answer=answer,
        meta={
            "mechanics.force_balance.intent": "find_components",
            "mechanics.force_balance.force_count": 1,
            "mechanics.force_balance.angle_deg": force.angle_deg,
            "mechanics.force_balance.fx": components.x,
            "mechanics.force_balance.fy": components.y,
        },
    )


def _solve_equilibrium(text: str, skill_name: str, skill_version: str) -> SolveResult:
    forces = _extract_forces(text)
    if len(forces) < 2:
        raise ValueError("equilibrium check requires at least two forces")
    if len(forces) > 3:
        raise ValueError("force_balance supports at most three forces in this phase")

    summed = Components(
        x=sum(_components(force).x for force in forces),
        y=sum(_components(force).y for force in forces),
    )
    is_balanced = _is_zero(summed.x) and _is_zero(summed.y)
    answer = "处于平衡" if is_balanced else "不处于平衡"
    steps = [
        Step(index=1, description=f"识别到 {len(forces)} 个力，分别分解到 x、y 方向"),
        Step(
            index=2,
            description="分别求两个方向的合力",
            formula_latex=(
                rf"\sum F_x={_format_number(summed.x)},"
                rf"\quad \sum F_y={_format_number(summed.y)}"
            ),
        ),
        Step(
            index=3,
            description="若两个方向合力都为 0，则系统平衡；否则不平衡",
            formula_latex=r"\sum F_x=0\ \mathrm{and}\ \sum F_y=0",
        ),
    ]
    return _result(
        intent="check_equilibrium",
        skill_name=skill_name,
        skill_version=skill_version,
        steps=steps,
        answer=answer,
        meta={
            "mechanics.force_balance.intent": "check_equilibrium",
            "mechanics.force_balance.force_count": len(forces),
            "mechanics.force_balance.sum_fx": summed.x,
            "mechanics.force_balance.sum_fy": summed.y,
            "mechanics.force_balance.is_balanced": is_balanced,
        },
    )


def _result(
    *,
    intent: Intent,
    skill_name: str,
    skill_version: str,
    steps: list[Step],
    answer: str | dict[str, str],
    meta: dict[str, object],
) -> SolveResult:
    template = _EXPLANATION_TEMPLATES[intent]
    meta = {
        "success": True,
        "skill_version": skill_version,
        "message": "已完成力学平衡分析。",
        **meta,
    }
    return SolveResult(
        question_type="force_balance",
        skill=skill_name,
        steps=steps,
        answer=answer,
        student_explanation=StudentExplanation(
            summary=template["summary"],
            intuition=template["intuition"],
            step_by_step=[_step_to_text(step) for step in steps],
            common_mistake=template["common_mistake"],
            self_check_question=template["self_check_question"],
        ),
        meta=meta,
    )


def _step_to_text(step: Step) -> str:
    if step.formula_latex:
        return f"{step.description}：${step.formula_latex}$"
    return step.description


def _detect_intent(text: str) -> Intent:
    lowered = text.lower()
    if any(keyword in lowered for keyword in ("分解", "分力", "component", "components", "resolve")):
        return "find_components"
    if any(keyword in lowered for keyword in ("是否平衡", "检查", "check", "equilibrium")):
        return "check_equilibrium"
    return "find_balanced_force"


def _single_force(text: str) -> Force:
    forces = _extract_forces(text)
    if not forces:
        raise ValueError("force_balance requires a force magnitude")
    return forces[0]


def _extract_forces(text: str) -> list[Force]:
    matches = list(_FORCE_QUANTITY_RE.finditer(text))
    forces: list[Force] = []
    for index, match in enumerate(matches):
        next_start = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        after = text[match.end() : min(next_start, match.end() + 80)]
        nearby = text[max(0, match.start() - 24) : min(len(text), match.end() + 80)]
        angle, label = _extract_angle_or_direction(after)
        if angle is None:
            angle, label = _extract_angle_or_direction(nearby)
        if angle is None:
            angle_match = _ANGLE_RE.search(text)
            if angle_match is not None:
                angle = float(angle_match.group(1))
                label = f"与 x 轴成 {_format_number(angle)}°"
        if angle is None:
            raise ValueError("force direction or angle is required")

        unit = _normalize_unit(match.group("unit"))
        forces.append(
            Force(
                magnitude=float(match.group("magnitude")),
                unit=unit,
                angle_deg=_normalize_angle(angle),
                label=label or _direction_label(angle),
            )
        )
    return forces


def _extract_angle_or_direction(text: str) -> tuple[float | None, str | None]:
    angle_match = _ANGLE_RE.search(text)
    if angle_match is not None:
        angle = float(angle_match.group(1))
        return angle, f"与 x 轴成 {_format_number(angle)}°"

    bare_angle_match = _BARE_ANGLE_RE.search(text)
    if bare_angle_match is not None:
        angle = float(bare_angle_match.group(1))
        return angle, f"与 x 轴成 {_format_number(angle)}°"

    lowered = text.lower()
    for keyword, angle, label in _DIRECTION_ANGLES:
        if keyword in lowered:
            return angle, label
    return None, None


def _components(force: Force) -> Components:
    radians = math.radians(force.angle_deg)
    return Components(
        x=_clean_float(force.magnitude * math.cos(radians)),
        y=_clean_float(force.magnitude * math.sin(radians)),
    )


def _has_force_quantity(text: str) -> bool:
    return _FORCE_QUANTITY_RE.search(text) is not None


def _normalize_unit(unit: str) -> str:
    lowered = unit.lower()
    if lowered == "kn":
        return "kN"
    if unit == "牛顿":
        return "N"
    return "N"


def _normalize_angle(angle: float) -> float:
    return _clean_float(angle % 360.0)


def _direction_label(angle: float) -> str:
    normalized = _normalize_angle(angle)
    if _is_close(normalized, 0.0) or _is_close(normalized, 360.0):
        return "向右"
    if _is_close(normalized, 90.0):
        return "向上"
    if _is_close(normalized, 180.0):
        return "向左"
    if _is_close(normalized, 270.0):
        return "向下"
    return f"与 x 轴成 {_format_number(normalized)}°"


def _format_number(value: float) -> str:
    clean = _clean_float(value)
    if float(clean).is_integer():
        return str(int(clean))
    return f"{clean:.2f}".rstrip("0").rstrip(".")


def _clean_float(value: float) -> float:
    if abs(value) < 1e-9:
        return 0.0
    rounded = round(value, 10)
    if abs(rounded - round(rounded)) < 1e-9:
        return float(round(rounded))
    return rounded


def _is_zero(value: float) -> bool:
    return abs(value) < 1e-7


def _is_close(left: float, right: float) -> bool:
    return abs(left - right) < 1e-7
