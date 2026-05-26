# M2 Routing Eval

Date: 2026-05-26

Command shape:

```bash
UV_CACHE_DIR=/tmp/examsolver-uv-cache uv run python scripts/smoke.py "<question>"
```

## 10-Sample Routing

| # | Question | Expected | Actual | Skill | Result |
|---|---|---|---|---|---|
| 1 | 求 x^2 对 x 的导数 | calculus / derivative | calculus / derivative | calculus.derivative | Pass |
| 2 | 求 sin(x) 在 0 处展开 | calculus / series or unknown | calculus / unknown | general.cot_with_textbook | Pass |
| 3 | 矩阵 [[1,2],[3,4]] 乘 [[5,6],[7,8]] | linear_algebra / matrix_mul | linear_algebra / matrix_mul | linear_algebra.matrix_mul | Pass |
| 4 | 三力平衡，10N 30N 求第三力 | mechanics_eng / force_balance | mechanics / force_balance | mechanics.force_balance | Pass with legacy subject alias |
| 5 | 汽车 ABS 起到什么作用？ | general / unknown | general / unknown | general.cot_with_textbook | Pass |
| 6 | H7/g6 是什么配合？ | tolerance / unknown | tolerance / unknown | general.cot_with_textbook | Pass |
| 7 | 齿轮 z1=20 z2=40 传动比？ | mechanism / unknown | mechanism / unknown | general.cot_with_textbook | Pass |
| 8 | 解释一下今天的天气 | general / unknown | general / unknown | general.cot_with_textbook | Pass |
| 9 | 拉格朗日中值定理证明 | calculus / unknown | calculus / unknown | general.cot_with_textbook | Pass |
| 10 | 请翻译 hello | general / unknown | general / unknown | general.cot_with_textbook | Pass |

Strict subject/type score: 9 / 10 = 90%.

Score with the current legacy `mechanics` subject accepted as the existing `mechanics_eng.force_balance` implementation slot: 10 / 10 = 100%.

## Local vs Cloud Provider Comparison

Compared two runs:

```bash
EXAMSOLVER_LLM_PROVIDER=local_gguf uv run python scripts/smoke.py "<question>"
EXAMSOLVER_LLM_PROVIDER=claude uv run python scripts/smoke.py "<question>"
```

| # | Local subject/type | Claude-provider subject/type | Match |
|---|---|---|---|
| 1 | calculus / derivative | calculus / derivative | Yes |
| 2 | calculus / unknown | calculus / unknown | Yes |
| 3 | linear_algebra / matrix_mul | linear_algebra / matrix_mul | Yes |
| 4 | mechanics / force_balance | mechanics / force_balance | Yes |
| 5 | general / unknown | general / unknown | Yes |
| 6 | tolerance / unknown | tolerance / unknown | Yes |
| 7 | mechanism / unknown | mechanism / unknown | Yes |
| 8 | general / unknown | general / unknown | Yes |
| 9 | calculus / unknown | calculus / unknown | Yes |
| 10 | general / unknown | general / unknown | Yes |

Consistency: 10 / 10 = 100%.

Note: this machine did not have `ANTHROPIC_API_KEY` set during the run. The `claude` provider path was exercised as a configured provider mode, then degraded through the router fallback path. Re-run with a valid Anthropic key to measure live cloud model behavior.

