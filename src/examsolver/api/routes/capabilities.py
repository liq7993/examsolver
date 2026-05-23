"""Capabilities route for registered skills."""

from __future__ import annotations

from fastapi import APIRouter

from examsolver.api.schemas import CapabilitiesBody, SkillCapabilityBody, SubjectCapabilityBody
from examsolver.skills.registry import all_skills

router = APIRouter(tags=["capabilities"])


@router.get("/solve/capabilities", response_model=CapabilitiesBody)
def capabilities() -> CapabilitiesBody:
    """Return subjects, question types, and skill versions from the registry."""

    skills = [
        SkillCapabilityBody(
            name=skill.name,
            version=skill.version,
            subject=skill.subject,
            question_types=skill.question_types,
        )
        for skill in all_skills()
    ]
    subjects: dict[str, set[str]] = {}
    for skill in all_skills():
        subjects.setdefault(skill.subject, set()).update(skill.question_types)

    return CapabilitiesBody(
        subjects=[
            SubjectCapabilityBody(name=subject, question_types=sorted(question_types))
            for subject, question_types in sorted(subjects.items())
        ],
        skills=skills,
    )
