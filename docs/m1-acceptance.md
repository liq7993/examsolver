# M1 Acceptance Report

Date: 2026-05-24

## Summary

M1 LangGraph integration is accepted. The solve service now runs through the compiled graph while preserving the public `solve()` signature and HTTP `/solve` response shape.

## Checks

| Command | Result |
|---|---|
| `uv run ruff check .` | passed: all checks passed |
| `uv run mypy src` | passed: no issues in 43 source files |
| `uv run pytest -q` | passed: 90 passed, 0 failed, 0 skipped |
| `uv run pytest -q tests/graph` | passed: 19 passed, 0 failed, 0 skipped |

## Smoke Output Summary

`uv run python scripts/smoke.py "求 x^2 对 x 的导数"`

- `success=true`
- `subject=calculus`
- `question_type=derivative`
- `skill=calculus.derivative`
- `answer="$\\frac{d}{dx}(x^2) = 2x$"`
- `note` is present and has the same `solve_id`.

`uv run python scripts/smoke.py "汽车 ABS 起到什么作用？"`

- `success=false`
- `subject=unknown`
- `question_type=unknown`
- `skill=unknown`
- `answer=null`
- `message="当前版本尚未支持此题型。"`
- `note` is present for the unsupported-question shell.

## HTTP Curl Summary

Server command:

```bash
uv run uvicorn examsolver.api.app:app --port 8765
```

`curl -X POST http://localhost:8765/solve -H "Content-Type: application/json" -d '{"question":"求 x^2 对 x 的导数"}'`

- HTTP 200
- Response body keeps the public API shape: `success`, `solve_id`, `subject`, `question_type`, `skill`, `steps`, `answer`, `message`, `student_explanation`.
- Summary: `success=true`, `subject=calculus`, `question_type=derivative`, `skill=calculus.derivative`.

`curl -X POST http://localhost:8765/solve -H "Content-Type: application/json" -d '{"question":"解释一下今天的天气"}'`

- HTTP 200
- Response body keeps the same public API shape.
- Summary: `success=false`, `subject=unknown`, `question_type=unknown`, `skill=unknown`, `answer=null`.

## Log Format Evidence

Observed smoke logs match `CONVENTIONS.md` section 4.3: `[<request_id>] <LEVEL> <module.function>: <message>`.

```text
[f5dd856b3ae74a3a8cf3141e0876deaf] INFO graph.nodes.normalize_node: done subject=calculus images=0
[f5dd856b3ae74a3a8cf3141e0876deaf] INFO graph.nodes.router_agent_node: subject=calculus question_type=derivative confidence=1.00
[f5dd856b3ae74a3a8cf3141e0876deaf] INFO graph.nodes.skill_node: skill=calculus.derivative
[f5dd856b3ae74a3a8cf3141e0876deaf] INFO graph.nodes.persist_node: done saved solve_id=c4fb6e70942f4ce8ada6354fe5a75030
[f5dd856b3ae74a3a8cf3141e0876deaf] INFO graph.build.run_solve_graph: done success=True
```

## Known Followups

- M2: replace the M1 unknown fallback with `general.cot_with_textbook` so general questions such as ABS can return structured answers.
- M2: upgrade `router_agent_node` from deterministic classifier fallback to real LLM routing with confidence reasoning.
- M3+: wire OCR, VLM, RAG, and citation-bearing textbook retrieval nodes.
- Logging: `normalize_node` begin currently logs `[unknown]` before normalization creates `request_id`; subsequent node logs use the real request id.
