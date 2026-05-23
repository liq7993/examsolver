"""Unknown fallback skill for unsupported question types."""

from __future__ import annotations

from examsolver.contracts import NormalizedQuestion, SolveResult


class UnknownSkill:
    """Normal fallback path when no concrete skill supports a question."""

    name = "unknown"
    version = "0.1.0"
    subject = "unknown"
    question_types = ["unknown"]

    def can_handle(self, question: NormalizedQuestion) -> bool:
        return True

    def solve(self, question: NormalizedQuestion) -> SolveResult:
        return SolveResult(
            question_type="unknown",
            skill=self.name,
            steps=[],
            answer=None,
            student_explanation=None,
            meta={
                "success": False,
                "skill_version": self.version,
                "message": "当前版本尚未支持此题型。",
            },
        )
