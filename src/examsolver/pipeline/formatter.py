"""Response formatting layer."""

from __future__ import annotations

from examsolver.contracts import NormalizedQuestion, SolveResponse, SolveResult, Step


def format_response(question: NormalizedQuestion, result: SolveResult) -> SolveResponse:
    """Seal a skill result into the stable SolveResponse contract."""

    success = bool(result.meta.get("success", result.skill != "unknown"))
    message = str(result.meta.get("message") or ("已完成求解。" if success else "当前版本尚未支持此题型。"))
    solve_id = str(question.hints["solve_id"])

    return SolveResponse(
        success=success,
        solve_id=solve_id,
        subject=question.subject,
        question_type=result.question_type,
        skill=result.skill,
        steps=[_step_to_text(step) for step in result.steps],
        answer=result.answer,
        message=message,
        student_explanation=result.student_explanation,
        citations=result.citations,
    )


def _step_to_text(step: Step) -> str:
    if step.formula_latex:
        return f"{step.description}：${step.formula_latex}$"
    return step.description
