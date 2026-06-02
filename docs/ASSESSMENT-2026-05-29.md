# Examsolver 项目评估 · 2026-05-29

> 阶段：M0/M1/M2 已完成，M3-09 由 Codex 在跑。GPT-OSS preset 已接入（待 GGUF 验证）。
> 用途：作为"接下来怎么走"的讨论底稿。可在 chat 中逐条展开。

---

## 0. 一句话结论

架构和流程的**底子是好的**（可追溯、有隔离、有记忆三层），
但有一个**致命短板**：你在本机**跑不了测试、跑不出 demo**，目前是"盲建"。
面试项目最怕"跑不起来"。**当务之急不是继续做 M4/M5，而是先打通"本机能跑 + 能 demo 一道题"。**

---

## 1. 做得对的（面试加分项）

| # | 亮点 | 为什么是加分项 |
|---|---|---|
| 1 | **可追溯架构**：同心圆 + 8 字段 Solve Contract + ADR 决策记录 | 任何代码都能回答"为什么这样写"，面试官最爱问 |
| 2 | **Skill 协议隔离**（禁 import langgraph/fastapi/其他 skill） | 真工程素养，不是 AI 套壳 |
| 3 | **LLM preset 抽象**：一个环境变量切 Gemma/GPT-OSS/云端，零代码改动 | 单拎出来能讲 5 分钟的设计点 |
| 4 | **诚实降级**：无网不假装看图，返回"图像理解需联网，已提取文字" | 体现懂"能力边界"，比吹全能高级 |
| 5 | **三层记忆**：规划文档 / MEMORY.md / Obsidian | 解决了"AI 协作上下文丢失"，多数人没意识到这是问题 |

---

## 2. 真实风险（按严重度排，#1 最要命）

### ✅ #1【已解决】本机跑不了测试 / 跑不了 demo —— 曾是最高优先级
- 原现状：系统 Python 3.10（缺 `datetime.UTC`，3.11+ 才有）；`uv` 不在 PATH；`.venv` 是 Linux 的（指向 `/home/.../cpython-3.11-linux`）。
- **修复（2026-05-29）**：装 uv 0.11.17 → uv 拉 CPython 3.11.15 → 重建 Windows venv → 装测试依赖 → `pytest` **180 passed, 3 skipped**。
- 以后跑测试（uv 未进 PATH，别用 `uv run` 否则拉 2.5GB torch）：
  ```powershell
  cd D:\examsolver\examsolver
  .\.venv\Scripts\python.exe -m pytest -q
  ```

### 🟠 #2 「整个机械系」对面试项目是陷阱
- 6 学科全覆盖 = 每个半成品。面试看**深度**不看广度。
- 建议聚焦 **2 个做到惊艳**：
  - **高数**（Type-D，sympy 确定性求导/积分，最稳，必定能 demo）
  - **机械原理图解**（Type-H，体现多模态杀手锏，差异化）
  - 其余学科先占位。

### 🔴 #3【证据升级】Codex 自主跑卡 = 一致性 + 正确性风险
- Codex 一张张领卡，但写的代码**未必符合 ARCHITECTURE.md，甚至会给错误答案**。
- **2026-05-29 demo 实锤**：`calculus.derivative` 被 Codex 实现成**手写正则**（架构明确要求 sympy）：
  - 只会幂函数 `a·x^n`；遇到 `sin(x)` 静默当成 `x`，返回 `1`（正解 `cos(x)`）——**自信地骗人**。
  - 完全解析不了时（第 99 行）**凭空假装题目是 `x^2`**。
  - 已用 sympy 重写（v0.2.0）：sin/链式/乘积/商法则全对；解析失败 → `raise SkillExecutionError` 触发诚实降级。
- 旧漏点：`NoteEntry` 注入 `SolveResponse.note`（demo 实跑确认现已注入，OK）。
- **教训**：卡片若不写明"必须 sympy"+"必须能解 sin(x)→cos(x)"这类验收样例，agent 会挑最省事的错误实现。光静态审查抓不到，**必须有人真跑一次 demo**。

### 🟡 #4 前端是黑箱
- `D:\codex file\ExamSolver`（Next.js 15 + React 19）真实状态、能否接后端，**一直没验证过**。
- 笔记式一页一题 + KaTeX + 导出是项目的"脸"，脸没打通后端再漂亮也 demo 不出来。

---

## 3. 建议的下一步（替代"继续做 M4/M5"）

目标：**两周内有一个能现场 demo 的版本。**

1. **修本机环境**（半天，解锁一切）：装 uv → 建对 Windows venv → `uv run pytest` 真正绿一次。
2. **端到端打通一道题**：文字题 →（高数 sympy）→ 笔记页渲染公式 → 导出 Word。证明全链路活着。
3. **再回头继续 Codex 的 M3-M5 卡。**

---

## 4. 记忆 / 切模型说明（供放心切换）

模型本身无记忆，记忆在三处，切模型不影响：

| 载体 | 同会话切模型 | 新开会话 |
|---|---|---|
| 当前对话 transcript | ✅ 新模型读全部历史 | ❌ |
| MEMORY.md / project_examsolver.md | ✅ | ✅ 跨会话在 |
| Obsidian + 8 份规划文档 | ✅ | ✅ 永久在硬盘 |

结论：**别怕切**。这套三层记忆就是为了让任何模型/Codex 都能接手。

---

## 5. Demo 实跑验证记录（2026-05-29 完成）

第一次在 Windows 本机真跑，暴露并修复了 4 个"演示才会出现"的问题：

| # | 问题 | 严重度 | 修复 |
|---|---|---|---|
| D1 | Windows 控制台中文乱码（GBK vs UTF-8） | 中 | `scripts/smoke.py` 启动自愈 stdout/stderr 为 UTF-8 |
| D2 | derivative 对 sin/e^x/ln **给错误答案** | 🔴 高 | sympy 重写，全部正确 |
| D3 | Type-D 用正则违背架构 | 🔴 高 | 改用 `sympy.diff` |
| D4 | 解析失败时**编造** `x^2` | 🔴 高 | 失败/含中文 → 抛错 → graph 诚实降级 |
| D5 | 测试硬编码 WSL 路径，Windows 必挂 | 中 | 改 `tmp_path` 自建临时文件 |

改动文件：`scripts/smoke.py`、`src/examsolver/skills/calculus/derivative.py`（v0.1.0→0.2.0）、`pyproject.toml`（+sympy）、7 个测试文件。
验证：`180 passed, 3 skipped`；`smoke.py "求 sin(x) 对 x 的导数"` → `cos(x)` ✓。

---

## 6. 待讨论 / 待定（在 chat 里继续）

- [ ] 聚焦哪 2 个学科做"惊艳 demo"？（建议：高数 + 机械原理图解）
- [x] ~~本机环境修复~~ → 已完成（见 §1、§5）
- [ ] 前端黑箱——什么时候验证 `D:\codex file\ExamSolver` 能否接后端？
- [ ] Codex 卡片工作流是否继续 / 怎么改（见下方 chat 讨论）。
- [ ] GPT-OSS GGUF 到位后的 X-03 验证（已写成 followup，待贴 BACKLOG）。
- [ ] 是否把本次改动 commit（项目当前未提交）。

---

*评估版本：v1.1 · 2026-05-29 · 加入 demo 实跑验证与 Codex 风险升级*
