"""Explicit skill registry."""

from __future__ import annotations

from examsolver.contracts import NormalizedQuestion
from examsolver.skills.base import Skill
from examsolver.skills.calculus import DerivativeSkill
from examsolver.skills.linear_algebra import MatrixMulSkill
from examsolver.skills.mechanics import ForceBalanceSkill
from examsolver.skills.unknown_skill import UnknownSkill

_UNKNOWN_SKILL = UnknownSkill()
_SKILLS_BY_NAME: dict[str, Skill] = {}
_QUESTION_TYPE_TO_SKILL_NAME: dict[str, str] = {}


def register(skill: Skill) -> None:
    """Register one skill instance and its supported question types."""

    _SKILLS_BY_NAME[skill.name] = skill
    for question_type in skill.question_types:
        _QUESTION_TYPE_TO_SKILL_NAME[question_type] = skill.name


def get_skill(name: str) -> Skill:
    """Return a skill by exact name or the unknown fallback."""

    return _SKILLS_BY_NAME.get(name, _UNKNOWN_SKILL)


def find_skill_for(question: NormalizedQuestion, question_type: str) -> Skill:
    """Find a skill by classified type, then by can_handle fallback."""

    skill_name = _QUESTION_TYPE_TO_SKILL_NAME.get(question_type)
    if skill_name is not None:
        return get_skill(skill_name)

    for skill in _SKILLS_BY_NAME.values():
        if skill.can_handle(question):
            return skill

    return _UNKNOWN_SKILL


def unknown_skill() -> Skill:
    """Return the singleton unknown fallback skill."""

    return _UNKNOWN_SKILL


def all_skills() -> list[Skill]:
    """Return registered concrete skills sorted by name."""

    return [_SKILLS_BY_NAME[name] for name in sorted(_SKILLS_BY_NAME)]


register(DerivativeSkill())
register(ForceBalanceSkill())
register(MatrixMulSkill())
