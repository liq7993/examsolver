"""Amplification eval: examsolver (deterministic core) vs the raw LLM, same model.

The north-star claim is "a weaker/cheaper LLM, wrapped in examsolver's deterministic
core, answers more questions correctly". This harness measures it on the golden set:

    arm A  examsolver : run each question through the real solve() pipeline
    arm B  raw LLM    : hand the same question straight to the configured cloud LLM

Both answers are graded with the *same* format-agnostic check (so neither arm is
favoured by output formatting), and real token usage is captured per arm.

    .venv/bin/python scripts/baseline_eval.py                 # full 42, both arms
    .venv/bin/python scripts/baseline_eval.py --limit 12      # quick subset
    .venv/bin/python scripts/baseline_eval.py --json out.json

Arm B needs a configured cloud provider + key (read from runtime settings / env);
without one it is skipped and only the examsolver arm is reported.
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from examsolver.contracts import SolveRequest  # noqa: E402
from examsolver.llm.base import Message  # noqa: E402
from examsolver.llm.router import pick_llm  # noqa: E402
from examsolver.runtime_settings import apply_to_environ, load_settings  # noqa: E402
from examsolver.services.solve_service import solve  # noqa: E402
from golden_eval import GOLDEN_SET, GoldenCase  # noqa: E402

apply_to_environ(load_settings(), override=False)

_PURE_LLM_PROMPT = (
    "你是严谨的理工科解题助手。解下面这道题，给出**化简后的最终答案**。\n"
    "矩阵给出每个元素，受力题给出大小和方向，配合题给出配合类型。\n"
    "最后一行用『答案：<最终答案>』给出，不要冗长推导。\n题目：{question}"
)

# Multi-step set: each case decomposes into a CHAIN of existing deterministic skills
# (二阶导 = 求导×2, 三阶导 = 求导×3, A·B·C = 矩阵乘×2). A single skill solves them only
# partially; examsolver's agentic loop plans the chain and runs each leaf deterministically.
# Raw LLMs lose accuracy here as derivatives/arithmetic compound -- exactly where the
# deterministic core amplifies a weaker model. not_contains catches partial answers
# (e.g. only the first matrix product).
MULTI_STEP_SET: list[GoldenCase] = [
    GoldenCase("d2_x3", "求 x^3 的二阶导数", "agentic.multi_step", ["6 x"]),
    GoldenCase("d2_x4", "求 x^4 的二阶导数", "agentic.multi_step", ["12 x^{2}"]),
    GoldenCase("d3_x5", "求 x^5 的三阶导数", "agentic.multi_step", ["60 x^{2}"]),
    GoldenCase(
        "matmul_chain_1",
        "计算 [[1,2],[3,4]] 乘 [[5,6],[7,8]] 再乘 [[1,0],[1,1]]",
        "agentic.multi_step",
        ["41", "22", "93", "50"],
        ["19", "43"],
    ),
    GoldenCase(
        "matmul_chain_2",
        "计算 [[3,2],[1,4]] 乘 [[2,1],[3,5]] 再乘 [[1,0],[2,1]]",
        "agentic.multi_step",
        ["38", "13", "56", "21"],
        ["12", "14"],
    ),
]

_TOKEN_RE = re.compile(r"tokens_in=(\d+) tokens_out=(\d+)")


class _TokenSink(logging.Handler):
    """Accumulate real token usage from the LLM clients' INFO log lines."""

    def __init__(self) -> None:
        super().__init__(level=logging.INFO)
        self.tokens = 0

    def reset(self) -> int:
        spent, self.tokens = self.tokens, 0
        return spent

    def emit(self, record: logging.LogRecord) -> None:
        match = _TOKEN_RE.search(record.getMessage())
        if match:
            self.tokens += int(match.group(1)) + int(match.group(2))


def _normalize(text: str) -> str:
    """Strip formatting so answers compare on content, not LaTeX/whitespace."""

    lowered = str(text).lower()
    return re.sub(r"[\s\\${}^_()*]+", "", lowered)


def _passes(answer: str, case: GoldenCase) -> bool:
    norm = _normalize(answer)
    return all(_normalize(f) in norm for f in case.expected_contains) and not any(
        _normalize(f) in norm for f in case.not_contains
    )


def _pure_llm_answer(case: GoldenCase) -> str:
    client = pick_llm("general_solve", needs_vision=False)
    if client is None:
        raise RuntimeError("no LLM configured")
    return client.chat(
        [Message(role="user", content=_PURE_LLM_PROMPT.format(question=case.question))],
        max_tokens=512,
        temperature=0.0,
        timeout=60.0,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="examsolver vs raw-LLM accuracy + tokens.")
    parser.add_argument("--limit", type=int, default=0, help="only the first N cases")
    parser.add_argument(
        "--multistep",
        action="store_true",
        help="evaluate the multi-step set (agentic loop) instead of the golden set",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    sink = _TokenSink()
    logging.getLogger("examsolver").addHandler(sink)
    logging.getLogger("examsolver").setLevel(logging.INFO)
    logging.disable(logging.NOTSET)

    source = MULTI_STEP_SET if args.multistep else GOLDEN_SET
    cases = source[: args.limit] if args.limit else source
    has_llm = pick_llm("general_solve", needs_vision=False) is not None
    if args.multistep and not has_llm:
        print(
            "note: the multi-step examsolver arm needs a configured cloud provider "
            "(the agentic loop uses it to PLAN); without one it degrades to fallback."
        )

    es_pass = es_tok = llm_pass = llm_tok = 0
    for case in cases:
        sink.reset()
        try:
            es_answer = str(solve(SolveRequest(question=case.question)).answer)
        except Exception as exc:  # noqa: BLE001
            es_answer = f"<crashed: {exc}>"
        es_ok = _passes(es_answer, case)
        es_pass += es_ok
        es_tok += sink.reset()

        llm_ok: bool | None = None
        if has_llm:
            try:
                llm_answer = _pure_llm_answer(case)
            except Exception as exc:  # noqa: BLE001
                llm_answer = f"<error: {exc}>"
            llm_ok = _passes(llm_answer, case)
            llm_pass += llm_ok
            llm_tok += sink.reset()

        if args.verbose:
            es_mark = "P" if es_ok else "F"
            llm_mark = "-" if llm_ok is None else ("P" if llm_ok else "F")
            print(f"[es:{es_mark} llm:{llm_mark}] {case.name}: {case.question[:40]}")

    total = len(cases)
    label = "multi-step / agentic" if args.multistep else "golden"
    print(f"\n=== Amplification eval [{label}]: {total} questions ===")
    print(f"examsolver : {es_pass}/{total} = {es_pass / total:.0%}   tokens≈{es_tok}")
    if has_llm:
        print(f"raw LLM    : {llm_pass}/{total} = {llm_pass / total:.0%}   tokens≈{llm_tok}")
        delta = (es_pass - llm_pass) / total
        print(f"Δ accuracy : {delta:+.0%}  (deterministic core over the same raw model)")
    else:
        print("raw LLM    : skipped (no cloud provider/key configured)")


if __name__ == "__main__":
    main()
