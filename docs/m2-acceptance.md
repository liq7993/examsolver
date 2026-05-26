# M2 Acceptance

Date: 2026-05-26

## Test Gates

| Gate | Result |
|---|---|
| `uv run ruff check .` | Pass |
| `uv run mypy src tests` | Pass, no issues in 80 source files |
| `uv run pytest -q` | Pass, 126 passed, 2 skipped |

## Routing Eval

10 smoke samples were run through `scripts/smoke.py`.

- Strict subject/type accuracy: 9 / 10 = 90%
- Accuracy with current `mechanics` subject accepted as the legacy implementation name for `mechanics_eng.force_balance`: 10 / 10 = 100%
- Local-vs-claude-provider subject/type consistency: 10 / 10 = 100%

Detailed sample table: [m2-routing-eval.md](m2-routing-eval.md)

## Smoke Checks

`uv run python scripts/smoke.py "求 x^2 对 x 的导数"`:

- subject: `calculus`
- question_type: `derivative`
- skill: `calculus.derivative`
- registry log included `registry: discovered 4 skills: [...]`

`uv run python scripts/smoke.py "汽车 ABS 起到什么作用？"`:

- subject: `general`
- question_type: `unknown`
- skill: `general.cot_with_textbook`
- note has structured steps, answer, and non-empty common mistakes
- registry log included `registry: discovered 4 skills: [...]`

## Known Followups

- The codebase currently uses `mechanics` as the implemented force-balance subject, while the roadmap vocabulary also refers to `mechanics_eng`. M2 acceptance treats this as a legacy alias, but M3+ should normalize the subject naming.
- Live cloud comparison was not available in this environment because `ANTHROPIC_API_KEY` was unset. The provider switch and fallback behavior were exercised; live Anthropic consistency should be rerun when credentials are present.
- Local llama-server returned 502 for route fallback calls during this run, so unsupported-domain routing relied on deterministic M2 subject hints and graceful fallback.

