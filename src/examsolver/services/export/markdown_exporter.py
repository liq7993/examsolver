"""Markdown export for a stored solve response."""

from __future__ import annotations

from typing import Any

from examsolver.contracts import SolveResponse


def export_to_markdown(*, question: str, response: SolveResponse) -> str:
    """Convert a solve snapshot into portable Markdown."""

    lines = [
        f"# Examsolver 解题笔记 · {response.subject or 'unknown'} / {response.question_type}",
        "",
        f"- Solve ID: `{response.solve_id}`",
        f"- Skill: `{response.skill}`",
        f"- Status: {'success' if response.success else 'unsupported'}",
        "",
        "## 题目",
        "",
        question,
        "",
        "## 最终答案",
        "",
        _format_answer(response.answer),
        "",
        "## 步骤",
        "",
    ]

    if response.steps:
        lines.extend(f"{index}. {step}" for index, step in enumerate(response.steps, start=1))
    else:
        lines.append("暂无步骤。")

    if response.student_explanation is not None:
        explanation = response.student_explanation
        lines.extend(
            [
                "",
                "## 学生解释",
                "",
                f"**总结**：{explanation.summary}",
                "",
                f"**直觉**：{explanation.intuition}",
                "",
                "**分步理解**：",
                "",
            ]
        )
        lines.extend(f"- {step}" for step in explanation.step_by_step)
        lines.extend(
            [
                "",
                f"**易错点**：{explanation.common_mistake}",
                "",
                f"**自检**：{explanation.self_check_question}",
            ]
        )

    lines.extend(["", f"> {response.message}", ""])
    return "\n".join(lines)


def _format_answer(answer: str | dict[str, Any] | None) -> str:
    if answer is None or answer == "":
        return "无答案"
    if isinstance(answer, str):
        return answer
    return "\n".join(f"- `{key}`: {value}" for key, value in answer.items())
