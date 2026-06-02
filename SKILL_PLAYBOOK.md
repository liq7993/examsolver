# Skill 编写手册 v1.0

> 怎么写一颗卫星（skill）。新增学科 / 新增题型必读。

---

## 0. 三型 skill 速查

| 型 | 名 | 何时用 | 代表 |
|---|---|---|---|
| Type-D | Deterministic（确定性）| 有闭式算法 / sympy 能跑 | `calculus.derivative` |
| Type-L | LLM-only | 开放题 / 主观题 / 大文本综合 | `auto_theory.dynamics` |
| Type-H | Hybrid | LLM 抽参数 → 算法求解 → LLM 解释 | `mechanism.gear_train` `tolerance.fit_type` |

**v1.0 主力是 Type-H**。它兼具 LLM 覆盖广 + 算法可回放的优点。

---

## 1. 共同接口

```python
from typing import Literal, Protocol
from examsolver.contracts import NormalizedQuestion, SolveResult
from examsolver.llm.base import LLMClient
from examsolver.rag.retriever import Retriever


class Skill(Protocol):
    name: str                                      # "<subject>.<question_type>"
    version: str                                   # SemVer "0.1.0"
    subject: str                                   # "mechanism"
    question_types: list[str]                      # ["gear_train"]
    skill_type: Literal["deterministic", "llm", "hybrid"]
    needs_vision: bool                             # 调度器据此决定是否跑 VLM
    needs_rag: bool                                # 据此决定是否跑 RAG

    def can_handle(self, question: NormalizedQuestion) -> bool: ...

    def solve(
        self,
        question: NormalizedQuestion,
        *,
        llm: LLMClient | None = None,
        rag: Retriever | None = None,
    ) -> SolveResult: ...
```

**注入而非全局**：LLM / RAG 通过参数。测试时 mock 容易。

---

## 2. 添加新 skill 的 5 步

### Step 1 · 用脚手架生成

```bash
python scripts/new_skill.py <subject> <question_type> --type=hybrid
```

生成：
```
src/examsolver/skills/<subject>/
├── _meta.py                      # 已存在则不动
├── _textbook/.gitkeep            # 已存在则不动
└── <question_type>.py            # 三个 TODO 区
tests/skills/<subject>/
├── <question_type>_regression.json
└── test_<question_type>.py
```

### Step 2 · 改三个 TODO 区

1. `can_handle` 判定逻辑
2. `solve` 主体
3. prompt 模板（如果 Type-L / Type-H）

### Step 3 · 写 ≥ 3 条回归 fixture

```json
[
  {
    "id": "gt-001",
    "question": "两级齿轮传动 z1=20 z2=40 z3=15 z4=60，传动比？",
    "expected_subject": "mechanism",
    "expected_question_type": "gear_train",
    "expected_answer_contains": "8"
  },
  ...
]
```

### Step 4 · 测试通过

```bash
uv run pytest tests/skills/<subject>/test_<question_type>.py
```

### Step 5 · 在 registry 注册

`skills/registry.py` 走自动发现，新文件被识别。如果文件命名特殊，手动加：

```python
from examsolver.skills.<subject>.<question_type> import <SkillClass>
REGISTRY.add(<SkillClass>())
```

---

## 3. Type-D 模板（Deterministic）

适用：闭式数学题，sympy / numpy 能搞定。

```python
"""skills/calculus/derivative.py — 求导（确定性）"""
from __future__ import annotations

import sympy as sp
from examsolver.contracts import NormalizedQuestion, SolveResult, Step
from examsolver.skills._base.deterministic import DeterministicSkill


class DerivativeSkill(DeterministicSkill):
    name = "calculus.derivative"
    version = "0.2.0"
    subject = "calculus"
    question_types = ["derivative"]
    needs_vision = False
    needs_rag = False

    def can_handle(self, question: NormalizedQuestion) -> bool:
        text = question.normalized_text.lower()
        return any(k in text for k in ("导数", "求导", "derivative", "d/dx"))

    def solve(self, question: NormalizedQuestion, **kwargs) -> SolveResult:
        expr_str, var_str = self._extract(question)
        x = sp.Symbol(var_str)
        expr = sp.sympify(expr_str)
        derivative = sp.diff(expr, x)
        return SolveResult(
            question_type="derivative",
            skill=self.name,
            skill_version=self.version,
            steps=[
                Step(index=1, description=f"识别表达式 {expr}",
                     formula_latex=sp.latex(expr), image_hint=None),
                Step(index=2, description=f"对 {var_str} 求导",
                     formula_latex=rf"\frac{{d}}{{d{var_str}}}\left({sp.latex(expr)}\right)",
                     image_hint=None),
                Step(index=3, description="化简",
                     formula_latex=sp.latex(derivative), image_hint=None),
            ],
            answer=f"$ {sp.latex(derivative)} $",
            student_explanation=None,
            citations=[],
            meta={"calculus.derivative.var": var_str},
        )

    def _extract(self, q: NormalizedQuestion) -> tuple[str, str]:
        ...  # 提取表达式与变量
```

**红线**：
- 不调 LLM、不调 RAG、不读文件
- 失败抛 `SkillExecutionError`，graph 走 general 兜底
- `student_explanation` 留空，由 enhancer 节点填

---

## 4. Type-L 模板（LLM-only）

适用：开放题、综合题、教材自由问答。

```python
"""skills/auto_theory/dynamics.py — 汽车动力性问答（LLM）"""
from __future__ import annotations
from pathlib import Path
import json

from examsolver.contracts import NormalizedQuestion, SolveResult, Step
from examsolver.llm.base import LLMClient, Message
from examsolver.skills._base.llm_skill import LLMSkill


_PROMPT = (Path(__file__).parent / "prompts" / "dynamics.zh.md").read_text(encoding="utf-8")

_SCHEMA = {
    "type": "object",
    "required": ["thinking", "steps", "answer", "common_mistakes"],
    "properties": {
        "thinking": {"type": "string"},
        "steps": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["description"],
                "properties": {
                    "description": {"type": "string"},
                    "formula_latex": {"type": ["string", "null"]},
                },
            },
        },
        "answer": {"type": "string"},
        "common_mistakes": {"type": "array", "items": {"type": "string"}},
    },
}


class DynamicsSkill(LLMSkill):
    name = "auto_theory.dynamics"
    version = "0.1.0"
    subject = "auto_theory"
    question_types = ["dynamics"]
    needs_vision = False
    needs_rag = False

    def can_handle(self, question: NormalizedQuestion) -> bool:
        text = question.normalized_text
        return any(k in text for k in ("动力性", "加速时间", "最高车速", "爬坡度"))

    def solve(self, question: NormalizedQuestion, *, llm: LLMClient, **_) -> SolveResult:
        msg = [
            Message(role="system", content=_PROMPT),
            Message(role="user", content=question.normalized_text),
        ]
        raw = llm.chat(msg, json_schema=_SCHEMA, max_tokens=1500, temperature=0.2)
        parsed = json.loads(raw)
        steps = [
            Step(index=i + 1, description=s["description"],
                 formula_latex=s.get("formula_latex"), image_hint=None)
            for i, s in enumerate(parsed["steps"])
        ]
        return SolveResult(
            question_type="dynamics",
            skill=self.name,
            skill_version=self.version,
            steps=steps,
            answer=parsed["answer"],
            student_explanation=None,
            citations=[],
            meta={
                "auto_theory.dynamics.thinking": parsed["thinking"],
                "auto_theory.dynamics.common_mistakes": parsed["common_mistakes"],
            },
        )
```

`prompts/dynamics.zh.md`：

```markdown
你是一名汽车理论的助教，针对学生考试题给出结构化答案。

输出严格 JSON：
- thinking: 一句话点破解题思路
- steps: 步骤数组，每步含 description 和可选 formula_latex
- answer: 最终结论（30-100 字）
- common_mistakes: 易错点 1-5 条

要求：
- 中文，准确，紧扣《汽车理论》课程
- 公式用 LaTeX
- 不要回答与题目无关的内容
```

**红线**：
- 必须用 `json_schema` 约束
- 解析失败重试 1 次，仍失败抛 `SkillExecutionError`
- prompt 文件独立，不内联

---

## 5. Type-H 模板（Hybrid）

适用：v1.0 主力。VLM / OCR / RAG 介入的场景。

### 5.1 例 A：`mechanism.gear_train`（VLM + 算法）

```python
"""skills/mechanism/gear_train.py"""
from __future__ import annotations
from pathlib import Path
import json

from examsolver.contracts import NormalizedQuestion, SolveResult, Step
from examsolver.llm.base import LLMClient, Message
from examsolver.skills._base.hybrid import HybridSkill


_PROMPT = (Path(__file__).parent / "prompts" / "gear_train_extract.zh.md").read_text(encoding="utf-8")

_EXTRACT_SCHEMA = {
    "type": "object",
    "required": ["stages"],
    "properties": {
        "stages": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["driving_teeth", "driven_teeth"],
                "properties": {
                    "driving_teeth": {"type": "integer"},
                    "driven_teeth": {"type": "integer"},
                },
            },
        }
    },
}


class GearTrainSkill(HybridSkill):
    name = "mechanism.gear_train"
    version = "0.1.0"
    subject = "mechanism"
    question_types = ["gear_train"]
    needs_vision = True          # 节点据此跑 VLM
    needs_rag = False

    def can_handle(self, question: NormalizedQuestion) -> bool:
        text = question.normalized_text
        return any(k in text for k in ("齿轮", "传动比", "齿数"))

    def solve(self, question: NormalizedQuestion, *, llm: LLMClient, **_) -> SolveResult:
        # 1. LLM 从文本 + 视觉描述抽参数
        ctx = f"题目：{question.normalized_text}\n图像描述：{question.vision_description or '无'}"
        raw = llm.chat(
            [Message(role="system", content=_PROMPT), Message(role="user", content=ctx)],
            json_schema=_EXTRACT_SCHEMA,
        )
        params = json.loads(raw)
        stages = params["stages"]

        # 2. 算法求传动比
        ratio = 1.0
        steps = []
        for i, st in enumerate(stages, start=1):
            r = st["driven_teeth"] / st["driving_teeth"]
            ratio *= r
            steps.append(Step(
                index=i,
                description=f"第 {i} 级：z{2*i-1}={st['driving_teeth']}, z{2*i}={st['driven_teeth']}, i_{i}={r}",
                formula_latex=rf"i_{i} = \frac{{z_{2*i}}}{{z_{2*i-1}}} = \frac{{{st['driven_teeth']}}}{{{st['driving_teeth']}}} = {r}",
                image_hint=None,
            ))
        steps.append(Step(
            index=len(stages) + 1,
            description="总传动比",
            formula_latex=rf"i = \prod i_k = {ratio}",
            image_hint=None,
        ))

        return SolveResult(
            question_type="gear_train",
            skill=self.name,
            skill_version=self.version,
            steps=steps,
            answer=f"总传动比 i = {ratio}",
            student_explanation=None,
            citations=[],
            meta={
                "mechanism.gear_train.ratio": ratio,
                "mechanism.gear_train.stages_count": len(stages),
            },
        )
```

### 5.2 例 B：`tolerance.fit_type`（RAG + LLM + 查表）

```python
"""skills/tolerance/fit_type.py"""
from __future__ import annotations
from pathlib import Path
import json

from examsolver.contracts import NormalizedQuestion, SolveResult, Step, Citation
from examsolver.llm.base import LLMClient, Message
from examsolver.rag.retriever import Retriever
from examsolver.skills._base.hybrid import HybridSkill
from examsolver.skills.tolerance._tables import lookup_basic_deviation


_PROMPT = (Path(__file__).parent / "prompts" / "fit_type_extract.zh.md").read_text(encoding="utf-8")


class FitTypeSkill(HybridSkill):
    name = "tolerance.fit_type"
    version = "0.1.0"
    subject = "tolerance"
    question_types = ["fit_type"]
    needs_vision = False
    needs_rag = True

    def can_handle(self, question: NormalizedQuestion) -> bool:
        text = question.normalized_text
        return any(k in text for k in ("配合", "H7", "g6", "公差带", "基本偏差"))

    def solve(
        self,
        question: NormalizedQuestion,
        *,
        llm: LLMClient,
        rag: Retriever,
        **_,
    ) -> SolveResult:
        # 1. RAG 检索教材
        chunks = rag.retrieve(query=question.normalized_text, subject="tolerance", top_k=3)
        textbook_ctx = "\n---\n".join(c.text for c in chunks) if chunks else "（无教材命中）"

        # 2. LLM 抽公差代号
        raw = llm.chat(
            [Message(role="system", content=_PROMPT),
             Message(role="user",
                     content=f"题目：{question.normalized_text}\n教材片段：{textbook_ctx}")],
            json_schema={
                "type": "object",
                "required": ["hole_symbol", "shaft_symbol"],
                "properties": {
                    "hole_symbol": {"type": "string"},
                    "shaft_symbol": {"type": "string"},
                },
            },
        )
        params = json.loads(raw)

        # 3. 查表
        hole = lookup_basic_deviation(params["hole_symbol"], "hole")
        shaft = lookup_basic_deviation(params["shaft_symbol"], "shaft")
        fit_type = _judge_fit_type(hole, shaft)

        # 4. 组装
        steps = [
            Step(index=1, description=f"识别孔代号 {params['hole_symbol']}",
                 formula_latex=None, image_hint=None),
            Step(index=2, description=f"识别轴代号 {params['shaft_symbol']}",
                 formula_latex=None, image_hint=None),
            Step(index=3, description=f"查表得孔基本偏差 {hole}，轴基本偏差 {shaft}",
                 formula_latex=None, image_hint=None),
            Step(index=4, description=f"判断为 {fit_type} 配合",
                 formula_latex=None, image_hint=None),
        ]
        citations = [
            Citation(source=c.document_title, chunk_id=c.id, page=c.page,
                     snippet=c.text[:200])
            for c in chunks
        ]
        return SolveResult(
            question_type="fit_type",
            skill=self.name,
            skill_version=self.version,
            steps=steps,
            answer=f"{params['hole_symbol']}/{params['shaft_symbol']} 属于{fit_type}配合",
            student_explanation=None,
            citations=citations,
            meta={
                "tolerance.fit_type.hole": hole,
                "tolerance.fit_type.shaft": shaft,
                "tolerance.fit_type.fit_type": fit_type,
            },
        )
```

**Type-H 的精髓**：
- LLM 只负责"抽取结构化参数"，不负责求解
- 求解用算法 / 查表，可单测可回放
- 解释由 enhancer 节点统一加

---

## 6. 测试模板

```python
"""tests/skills/mechanism/test_gear_train.py"""
import json
from pathlib import Path
import pytest

from examsolver.contracts import NormalizedQuestion
from examsolver.skills.mechanism.gear_train import GearTrainSkill
from tests._helpers.fake_llm import FakeLLMClient


FIXTURES = json.loads(
    (Path(__file__).parent / "gear_train_regression.json").read_text(encoding="utf-8")
)


def _make_q(text: str, vision: str = "") -> NormalizedQuestion:
    return NormalizedQuestion(
        raw_text=text,
        normalized_text=text,
        subject="mechanism",
        has_image=bool(vision),
        image_paths=[],
        ocr_text="",
        vision_description=vision,
        hints={"request_id": "test"},
    )


@pytest.mark.parametrize("case", FIXTURES, ids=lambda c: c["id"])
def test_gear_train(case):
    skill = GearTrainSkill()
    fake_llm = FakeLLMClient.from_recorded(case["llm_response"])
    q = _make_q(case["question"], case.get("vision", ""))

    assert skill.can_handle(q)
    result = skill.solve(q, llm=fake_llm)

    assert result.skill == "mechanism.gear_train"
    assert case["expected_answer_contains"] in result.answer
    assert result.meta["mechanism.gear_train.ratio"] == pytest.approx(case["expected_ratio"])
```

`gear_train_regression.json`：

```json
[
  {
    "id": "gt-001",
    "question": "两级齿轮传动，z1=20, z2=40, z3=15, z4=60，传动比？",
    "vision": "",
    "llm_response": "{\"stages\":[{\"driving_teeth\":20,\"driven_teeth\":40},{\"driving_teeth\":15,\"driven_teeth\":60}]}",
    "expected_answer_contains": "8",
    "expected_ratio": 8.0
  }
]
```

---

## 7. 行星 `_meta.py`

每个 subject 文件夹下：

```python
"""skills/mechanism/_meta.py"""
SUBJECT_META = {
    "subject": "mechanism",
    "display_name": "机械原理",
    "color": "#4a90e2",                # 前端显示用
    "icon": "gear",
    "has_textbook": False,             # 是否启用 RAG
    "textbook_path": None,             # 启用时指向 data/textbooks/
}
```

供前端 `/library` 与笔记页 chip 显示用。

---

## 8. 常见问题

**Q：我要写的 skill 在已有 subject 下，但属于新题型怎么办？**
A：在 `skills/<subject>/` 下加一个新 `.py`，更新 `_meta.py` 的 question_types（如果维护了的话），registry 会自动发现。

**Q：能不能在 skill 里调另一个 skill？**
A：不能。共享逻辑提到 `skills/_utils/` 或 `skills/<subject>/_helpers.py`。

**Q：skill 失败了 graph 会怎样？**
A：抛 `SkillExecutionError` → graph 捕获 → 走 `general_node` 兜底 → response.success=true, fallback_reasons 标记 "primary_skill_failed"。**永远不返回 500**。

**Q：Type-H 的 LLM 调用万一返回非 JSON 怎么办？**
A：`llm.chat(json_schema=...)` 内部已 retry 1 次。仍失败则抛 `LLMParseError`，被 graph 捕获走兜底。

**Q：怎么调试 prompt？**
A：用 `python scripts/smoke.py "<题>" --debug` 会把 LLM 入参出参打到 stderr。

**Q：能不能加临时 skill 给自己用，不进 registry？**
A：临时实验放 `scripts/experiments/`，不要污染 `skills/`。

---

## 9. 命名约定速查

| 对象 | 例 |
|---|---|
| `subject` | `mechanism` |
| `question_type` | `gear_train` |
| 文件 | `skills/mechanism/gear_train.py` |
| 类 | `GearTrainSkill` |
| `name` | `"mechanism.gear_train"` |
| Fixture | `tests/skills/mechanism/gear_train_regression.json` |
| Prompt 文件 | `skills/mechanism/prompts/gear_train_extract.zh.md` |
| meta 字段 | `meta["mechanism.gear_train.ratio"]` |

---

## 10. 写完一颗新 skill 自检清单

- [ ] `can_handle` 在 happy + 负样本上都正确
- [ ] `solve` 在 ≥ 3 条 fixture 全绿
- [ ] 失败情况抛 `SkillExecutionError`，不抛通用 Exception
- [ ] 不 import `langgraph` / `fastapi` / `sqlite3`
- [ ] 不 import 其他 skill
- [ ] prompt 在独立 `.md` 文件
- [ ] meta 字段带 `<subject>.<type>.` 前缀
- [ ] version 是 SemVer
- [ ] `needs_vision` / `needs_rag` 与实际行为一致
- [ ] `python scripts/smoke.py "<样例题>"` 走通

全勾才算完成。

---

## 11. 防偷懒：派 skill 卡给 agent（Codex）的规约

> **真实事故（2026-05-29）**：`calculus.derivative` 这张 Type-D 卡被 agent 实现成**手写正则**
> （架构明确要求 sympy）。结果：只会幂函数 `a·x^n`；遇到 `sin(x)` 静默当成 `x`、返回 `1`
> （正解 `cos(x)`）——**自信地骗人**；解析失败时（旧第 99 行）**凭空假装题目是 `x^2`**。
> 而且单测全绿、静态 review 也没抓到。是真跑一次 demo 才暴露的。
>
> 教训：**只给目标，agent 会挑最省事的错误实现**。卡片必须堵死偷懒路径。

### 11.1 每张 skill 卡必带"四件套"

```
【硬约束】必须 / 禁止。例：
  - 必须用 sympy 求解，禁止用正则解析数学表达式
  - 禁止 import 其他 skill / langgraph / fastapi / sqlite3（见 §13 红线）
  - 解析失败必须 raise SkillExecutionError，禁止编造一个默认答案

【正例】具体输入 → 期望输出，至少 2 条，覆盖核心能力（不止幂函数那种最简单的）。
  例：sin(x) → cos(x)；x·sin(x) → sin(x)+x·cos(x)（乘积法则）

【反例】边界 / 非法 / 能力外输入 → 期望的诚实行为（降级 / 报错 / 不编造），至少 1 条。
  例："这道题图里有个齿轮，求它的导数" → raise SkillExecutionError（不许返回 x^2）

【验证门】真跑什么命令确认卡真完成（不是"看起来完成"）：
  - .\.venv\Scripts\python.exe -m pytest tests/skills/<subject>/ -q
  - .\.venv\Scripts\python.exe scripts\smoke.py "<正例题>" → 人眼确认答案对
  - .\.venv\Scripts\python.exe scripts\smoke.py "<反例题>" → 确认走了诚实降级
```

### 11.2 三条铁律

1. **Type-D / Type-H 卡必须写反例**。诚实降级是产品卖点（见 ARCHITECTURE §11、§6.3），
   而 agent 默认不会主动做——不写明就会编造答案兜底。
2. **正例要覆盖"非平凡"分支**。只给 `x^2 → 2x` 这种最简单的，agent 就只实现幂函数。
   必须显式列 `sin/链式/乘积/商` 这类样例当验收锚点。
3. **完成判定 = 真跑验证门，不是测试绿**。derivative 的 bug 正是测试覆盖不到边界才溜过的。
   任何 skill 卡 review，**必须有人真跑一次 smoke.py 正例 + 反例**。

### 11.3 卡片骨架（复制改用）

```
### <编号> · <skill 名>
所属：<M?>   类型：Type-D/L/H   前置：<依赖>

【上下文】为什么做 + agent 需知道的既有事实（契约字段、可用 helper、相关 _tables）。
不要让 agent 自己猜架构——猜就会偏离 ARCHITECTURE.md。

【硬约束】必须 / 禁止（见 §11.1）
【出口】可勾选的文件产出 + 行为清单
【正例】≥2 条，含非平凡分支
【反例】≥1 条，期望诚实降级 / 报错
【验证门】pytest + smoke.py 正例反例各跑一遍
```

> 完整的里程碑级卡片清单（M4/M5 等）维护在 `D:\claude_memory\examsolver_goal_cards.md`，
> 本节只固化"怎么写一张防偷懒的 skill 卡"的方法论。

---

*文档状态：v1.1 · 2026-05-29 加入 §11 防偷懒规约（吸取 derivative bug 教训）。新写 skill 时若发现模板有改进空间，先改本文件再写代码。*
