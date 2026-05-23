from examsolver.contracts import NormalizedQuestion
from examsolver.skills.unknown_skill import UnknownSkill


def test_unknown_skill_returns_standard_fallback_result() -> None:
    result = UnknownSkill().solve(
        NormalizedQuestion(raw_text="?", normalized_text="?", subject="unknown", hints={})
    )

    assert result.question_type == "unknown"
    assert result.skill == "unknown"
    assert result.steps == []
    assert result.answer is None
    assert result.meta["success"] is False
