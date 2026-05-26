import logging

from pytest import LogCaptureFixture

from examsolver.skills import registry


def test_registry_discovers_skill_modules_and_logs(caplog: LogCaptureFixture) -> None:
    registry._reset_for_tests()
    caplog.set_level(logging.INFO, logger="examsolver.skills.registry")

    skills = registry.all_skills()

    names = {skill.name for skill in skills}
    assert len(skills) >= 4
    assert {
        "calculus.derivative",
        "linear_algebra.matrix_mul",
        "mechanics.force_balance",
        "general.cot_with_textbook",
    }.issubset(names)
    assert any("registry: discovered" in record.getMessage() for record in caplog.records)


def test_get_skill_uses_subject_and_question_type() -> None:
    registry._reset_for_tests()

    derivative = registry.get_skill("calculus", "derivative")
    matrix_mul = registry.get_skill("linear_algebra", "matrix_mul")
    force_balance = registry.get_skill("mechanics", "force_balance")
    general = registry.get_skill("general", "unknown")

    assert derivative is not None
    assert matrix_mul is not None
    assert force_balance is not None
    assert general is not None
    assert derivative.name == "calculus.derivative"
    assert matrix_mul.name == "linear_algebra.matrix_mul"
    assert force_balance.name == "mechanics.force_balance"
    assert general.name == "general.cot_with_textbook"
    assert registry.get_skill("missing", "derivative") is None


def test_list_skills_returns_serializable_metadata() -> None:
    registry._reset_for_tests()

    listed = registry.list_skills()

    derivative = next(item for item in listed if item["name"] == "calculus.derivative")
    assert derivative == {
        "subject": "calculus",
        "name": "calculus.derivative",
        "version": "0.1.0",
        "question_types": ["derivative"],
    }
