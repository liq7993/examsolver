"""Run one solve through the core chain without HTTP or storage."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from examsolver.contracts import SolveRequest  # noqa: E402
from examsolver.services.solve_service import solve  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Solve one question through Examsolver core.")
    parser.add_argument("question", nargs="?", default="求 x^2 对 x 的导数")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    response = solve(SolveRequest(question=args.question))
    print(json.dumps(_to_jsonable(response), ensure_ascii=False, indent=2))


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    return value


if __name__ == "__main__":
    main()
