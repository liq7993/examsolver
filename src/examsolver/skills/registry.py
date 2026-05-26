"""Auto-discovered skill registry."""

from __future__ import annotations

import importlib
import inspect
import logging
import pkgutil
from types import ModuleType
from typing import Any, cast

from examsolver.contracts import NormalizedQuestion
from examsolver.skills import __path__ as skills_package_path
from examsolver.skills.base import Skill
from examsolver.skills.unknown_skill import UnknownSkill

logger = logging.getLogger(__name__)

_UNKNOWN_SKILL = UnknownSkill()
_SKILLS_BY_ROUTE: dict[tuple[str, str], Skill] = {}
_SKILLS_BY_NAME: dict[str, Skill] = {}
_DISCOVERED = False
_SKIP_MODULE_NAMES = {"base", "registry", "unknown_skill"}


def get_skill(subject: str, question_type: str) -> Skill | None:
    """Return a concrete skill by ``(subject, question_type)``."""

    _ensure_discovered()
    return _SKILLS_BY_ROUTE.get((subject, question_type))


def list_skills() -> list[dict[str, object]]:
    """Return serializable registry metadata sorted by skill name."""

    _ensure_discovered()
    return [
        {
            "subject": skill.subject,
            "name": skill.name,
            "version": skill.version,
            "question_types": list(skill.question_types),
        }
        for skill in all_skills()
    ]


def register(skill: Skill) -> None:
    """Register one skill instance and its supported routes."""

    _SKILLS_BY_NAME[skill.name] = skill
    for question_type in skill.question_types:
        _SKILLS_BY_ROUTE[(skill.subject, question_type)] = skill


def find_skill_for(question: NormalizedQuestion, question_type: str) -> Skill:
    """Find a skill by subject/type, then by can_handle fallback."""

    _ensure_discovered()
    routed = get_skill(question.subject, question_type)
    if routed is not None:
        return routed

    for skill in all_skills():
        if skill.can_handle(question):
            return skill

    return _UNKNOWN_SKILL


def unknown_skill() -> Skill:
    """Return the singleton unknown fallback skill."""

    return _UNKNOWN_SKILL


def all_skills() -> list[Skill]:
    """Return discovered concrete skills sorted by name."""

    _ensure_discovered()
    return [_SKILLS_BY_NAME[name] for name in sorted(_SKILLS_BY_NAME)]


def _reset_for_tests() -> None:
    """Clear registry state so tests can force a fresh discovery pass."""

    global _DISCOVERED
    _SKILLS_BY_ROUTE.clear()
    _SKILLS_BY_NAME.clear()
    _DISCOVERED = False


def _ensure_discovered() -> None:
    global _DISCOVERED
    if _DISCOVERED:
        return
    _discover()
    _DISCOVERED = True
    names = sorted(_SKILLS_BY_NAME)
    logger.info("registry: discovered %d skills: %s", len(names), names)


def _discover() -> None:
    for module_info in pkgutil.walk_packages(skills_package_path, prefix="examsolver.skills."):
        module_name = module_info.name
        if module_info.ispkg or _should_skip_module(module_name):
            continue
        try:
            module = importlib.import_module(module_name)
        except Exception as exc:
            logger.warning("registry: skip module %s import failed: %s", module_name, exc)
            continue
        for skill_class in _skill_classes(module):
            try:
                register(cast(Skill, skill_class()))
            except Exception as exc:
                logger.warning(
                    "registry: skip skill %s.%s construction failed: %s",
                    skill_class.__module__,
                    skill_class.__name__,
                    exc,
                )


def _should_skip_module(module_name: str) -> bool:
    leaf = module_name.rsplit(".", 1)[-1]
    return leaf.startswith("_") or leaf in _SKIP_MODULE_NAMES


def _skill_classes(module: ModuleType) -> list[type[Any]]:
    classes: list[type[Any]] = []
    for _, candidate in inspect.getmembers(module, inspect.isclass):
        if candidate.__module__ != module.__name__:
            continue
        if _looks_like_skill_class(candidate):
            classes.append(candidate)
    return classes


def _looks_like_skill_class(candidate: type[Any]) -> bool:
    return (
        isinstance(getattr(candidate, "name", None), str)
        and isinstance(getattr(candidate, "version", None), str)
        and isinstance(getattr(candidate, "subject", None), str)
        and _is_string_list(getattr(candidate, "question_types", None))
    )


def _is_string_list(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)
