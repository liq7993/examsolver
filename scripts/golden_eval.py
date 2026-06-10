"""Golden-set evaluation: measure answer accuracy and citation hit rate offline.

Runs a fixed set of questions through the full solve graph (no LLM, no HTTP)
and grades each answer against independently written expectations:

    .venv/bin/python scripts/golden_eval.py            # summary
    .venv/bin/python scripts/golden_eval.py -v         # per-case detail
    .venv/bin/python scripts/golden_eval.py --json out.json

Grading is substring-based on the final ``SolveResponse.answer`` so it checks
the whole pipeline (normalize -> router -> skill -> format), not the skill in
isolation. Citation hit rate is measured on textbook-backed (tolerance) cases.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from examsolver.contracts import SolveRequest  # noqa: E402
from examsolver.services.solve_service import solve  # noqa: E402


@dataclass(frozen=True)
class GoldenCase:
    name: str
    question: str
    expected_skill: str
    expected_contains: list[str]
    not_contains: list[str] = field(default_factory=list)
    expects_citations: bool = False


GOLDEN_SET: list[GoldenCase] = [
    # ---------------- calculus.derivative ----------------
    GoldenCase("deriv_power", "求 x^2 对 x 的导数", "calculus.derivative", ["2 x"]),
    GoldenCase("deriv_coeff_power", "求 3x^3 的导数", "calculus.derivative", ["9 x^{2}"]),
    GoldenCase("deriv_sin", "求 sin(x) 对 x 的导数", "calculus.derivative", ["\\cos"]),
    GoldenCase("deriv_cos", "求 cos(x) 对 x 的导数", "calculus.derivative", ["- \\sin"]),
    GoldenCase("deriv_product", "对 x*sin(x) 求导", "calculus.derivative", ["\\sin", "\\cos"]),
    GoldenCase("deriv_power5", "求 x^5 对 x 的导数", "calculus.derivative", ["5 x^{4}"]),
    GoldenCase("deriv_poly_sum", "求 2x^2 + 3x 的导数", "calculus.derivative", ["4 x + 3"]),
    GoldenCase("deriv_poly_diff", "求 x^4 - x^2 的导数", "calculus.derivative", ["4 x^{3} - 2 x"]),
    GoldenCase("deriv_tan", "求 tan(x) 对 x 的导数", "calculus.derivative", ["\\tan"]),
    GoldenCase("deriv_xcos", "求 x*cos(x) 的导数", "calculus.derivative", ["\\cos", "\\sin"]),
    GoldenCase("deriv_linear", "求 5x 的导数", "calculus.derivative", ["= 5"]),
    GoldenCase(
        "deriv_x2sin", "求 x^2*sin(x) 的导数", "calculus.derivative", ["\\cos", "2 x \\sin"]
    ),
    # ---------------- linear_algebra.matrix_mul ----------------
    GoldenCase(
        "matmul_2x2",
        "计算矩阵 [[1,2],[3,4]] 乘 [[5,6],[7,8]]",
        "linear_algebra.matrix_mul",
        ["19", "22", "43", "50"],
    ),
    GoldenCase(
        "matmul_scale",
        "计算矩阵 [[2,0],[0,2]] 乘 [[1,2],[3,4]]",
        "linear_algebra.matrix_mul",
        ["2", "4", "6", "8"],
    ),
    GoldenCase(
        "matmul_identity",
        "计算矩阵 [[1,0],[0,1]] 乘 [[7,8],[9,10]]",
        "linear_algebra.matrix_mul",
        ["7", "8", "9", "10"],
    ),
    GoldenCase(
        "matmul_dot",
        "计算矩阵 [[1,2,3]] 乘 [[1],[2],[3]]",
        "linear_algebra.matrix_mul",
        ["14"],
    ),
    GoldenCase(
        "matmul_ones",
        "计算矩阵 [[1,1],[1,1]] 乘 [[2,2],[2,2]]",
        "linear_algebra.matrix_mul",
        ["4"],
    ),
    GoldenCase(
        "matmul_general",
        "计算矩阵 [[3,1],[2,4]] 乘 [[1,5],[2,3]]",
        "linear_algebra.matrix_mul",
        ["5", "18", "10", "22"],
    ),
    GoldenCase(
        "matmul_permute",
        "计算矩阵 [[0,1],[1,0]] 乘 [[1,2],[3,4]]",
        "linear_algebra.matrix_mul",
        ["3", "4", "1", "2"],
    ),
    GoldenCase(
        "matmul_vector",
        "计算矩阵 [[2,3],[4,5]] 乘 [[6],[7]]",
        "linear_algebra.matrix_mul",
        ["33", "59"],
    ),
    # ---------------- mechanics.force_balance ----------------
    GoldenCase(
        "force_balance_right",
        "一个 15 N 的力向右作用，求它的平衡力。",
        "mechanics.force_balance",
        ["15", "方向向左"],
    ),
    GoldenCase(
        "force_balance_up",
        "一个 8 N 的力向上作用，求它的平衡力。",
        "mechanics.force_balance",
        ["8", "方向向下"],
    ),
    GoldenCase(
        "force_balance_en",
        "Find the equilibrant of a 20 N force to the left.",
        "mechanics.force_balance",
        ["20", "方向向右"],
    ),
    GoldenCase(
        "force_components_60",
        "将 10 N、与 x 轴成 60 度的力分解为 x、y 分量。",
        "mechanics.force_balance",
        ["8.66"],
    ),
    GoldenCase(
        "force_components_45",
        "Resolve a 30 N force at 45 deg into x and y components.",
        "mechanics.force_balance",
        ["21.21"],
    ),
    GoldenCase(
        "force_equilibrium_yes",
        "检查 12 N 向右和 12 N 向左是否平衡。",
        "mechanics.force_balance",
        ["处于平衡"],
        not_contains=["不处于平衡"],
    ),
    GoldenCase(
        "force_equilibrium_no",
        "检查 9N 向右和 4N 向左是否平衡。",
        "mechanics.force_balance",
        ["不处于平衡"],
    ),
    GoldenCase(
        "force_balance_kn",
        "一个 3 kN 的力向左作用，求它的平衡力。",
        "mechanics.force_balance",
        ["3", "kN", "方向向右"],
    ),
    GoldenCase(
        "force_components_30",
        "将 20 N、与 x 轴成 30 度的力分解为 x、y 分量。",
        "mechanics.force_balance",
        ["17.32"],
    ),
    GoldenCase(
        "force_equilibrium_angles",
        "检查 10N 与 x 轴成 0 度和 10N 与 x 轴成 180 度是否平衡。",
        "mechanics.force_balance",
        ["处于平衡"],
        not_contains=["不处于平衡"],
    ),
    # ---------------- tolerance.fit_type (textbook-backed) ----------------
    GoldenCase(
        "fit_H7_g6", "H7/g6 是什么配合？", "tolerance.fit_type", ["间隙配合"], expects_citations=True
    ),
    GoldenCase(
        "fit_H7_h6",
        "H7/h6 的配合类型如何判断？",
        "tolerance.fit_type",
        ["间隙配合"],
        expects_citations=True,
    ),
    GoldenCase(
        "fit_H7_k6",
        "H7/k6 是间隙配合还是过渡配合？",
        "tolerance.fit_type",
        ["过渡配合"],
        expects_citations=True,
    ),
    GoldenCase(
        "fit_K7_h6",
        "K7/h6 的孔轴配合类型是什么？",
        "tolerance.fit_type",
        ["过渡配合"],
        expects_citations=True,
    ),
    GoldenCase(
        "fit_G7_g6",
        "G7/g6 应判为什么配合？",
        "tolerance.fit_type",
        ["间隙配合"],
        expects_citations=True,
    ),
    GoldenCase(
        "fit_H8_h7", "H8/h7 是什么配合？", "tolerance.fit_type", ["间隙配合"], expects_citations=True
    ),
    GoldenCase(
        "fit_H6_g5",
        "H6/g5 属于什么配合类型？",
        "tolerance.fit_type",
        ["间隙配合"],
        expects_citations=True,
    ),
    GoldenCase(
        "fit_H8_k7",
        "H8/k7 是什么类型的配合？",
        "tolerance.fit_type",
        ["过渡配合"],
        expects_citations=True,
    ),
    GoldenCase(
        "fit_K6_h5", "K6/h5 是什么配合？", "tolerance.fit_type", ["过渡配合"], expects_citations=True
    ),
    GoldenCase(
        "fit_H9_h9", "H9/h9 是什么配合？", "tolerance.fit_type", ["间隙配合"], expects_citations=True
    ),
    GoldenCase(
        "fit_explicit",
        "判断 H7 孔与 g6 轴的配合类型。",
        "tolerance.fit_type",
        ["间隙配合"],
        expects_citations=True,
    ),
    GoldenCase(
        "fit_G6_g5", "G6/g5 是什么配合？", "tolerance.fit_type", ["间隙配合"], expects_citations=True
    ),
]


def grade(case: GoldenCase) -> dict[str, object]:
    started = time.perf_counter()
    try:
        response = solve(SolveRequest(question=case.question))
    except Exception as exc:  # honest failure: a crash is a wrong answer
        return {
            "name": case.name,
            "passed": False,
            "skill_ok": False,
            "citations": 0,
            "elapsed_s": round(time.perf_counter() - started, 3),
            "answer": f"<crashed: {exc}>",
        }
    answer = str(response.answer)
    passed = (
        response.success
        and all(fragment in answer for fragment in case.expected_contains)
        and not any(fragment in answer for fragment in case.not_contains)
    )
    return {
        "name": case.name,
        "passed": passed,
        "skill_ok": response.skill == case.expected_skill,
        "citations": len(response.citations),
        "elapsed_s": round(time.perf_counter() - started, 3),
        "answer": answer,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the golden-set evaluation offline.")
    parser.add_argument("-v", "--verbose", action="store_true", help="print per-case results")
    parser.add_argument("--json", metavar="PATH", help="write the full report as JSON")
    args = parser.parse_args()

    logging.disable(logging.WARNING)

    results = []
    for case in GOLDEN_SET:
        outcome = grade(case)
        results.append((case, outcome))
        if args.verbose:
            mark = "PASS" if outcome["passed"] else "FAIL"
            print(f"[{mark}] {case.name}: {case.question}")
            if not outcome["passed"]:
                print(f"       expected {case.expected_contains}, got: {outcome['answer']}")

    total = len(results)
    passed = sum(1 for _, outcome in results if outcome["passed"])
    routed = sum(1 for _, outcome in results if outcome["skill_ok"])
    cited_cases = [(case, outcome) for case, outcome in results if case.expects_citations]
    cited_hits = sum(1 for _, outcome in cited_cases if int(str(outcome["citations"])) > 0)

    by_skill: dict[str, list[bool]] = {}
    for case, outcome in results:
        by_skill.setdefault(case.expected_skill, []).append(bool(outcome["passed"]))

    print(f"\n=== Golden set: {total} questions ===")
    print(f"answer accuracy : {passed}/{total} = {passed / total:.1%}")
    print(f"routing accuracy: {routed}/{total} = {routed / total:.1%}")
    if cited_cases:
        print(
            f"citation hit    : {cited_hits}/{len(cited_cases)} = "
            f"{cited_hits / len(cited_cases):.1%} (textbook-backed questions)"
        )
    for skill, marks in sorted(by_skill.items()):
        print(f"  {skill:30s} {sum(marks)}/{len(marks)}")

    if args.json:
        report = {
            "total": total,
            "answer_accuracy": passed / total,
            "routing_accuracy": routed / total,
            "citation_hit_rate": cited_hits / len(cited_cases) if cited_cases else None,
            "cases": [outcome for _, outcome in results],
        }
        Path(args.json).write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"report written to {args.json}")

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
