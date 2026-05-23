# Examsolver

> 大学生期末突击复习助手 · 同心圆 + LangGraph 架构 · 面试主作品

**这是什么**：一个把"上课没听、教材自编、搜题搜不到、图看不清"的大学生在期末前 48 小时救回来的工具。一题一页笔记，可导出 Word / PDF，公式渲染、机械图理解、错题归纳、突击卡片。机械系全覆盖优先，其他学科按需扩展。

**它不是**：搜题软件、AI 套壳问答框、通用 GPT 客户端。

---

## 当前状态（2026-05 重启后）

- 路线：**B 路线**（面试主作品 + 大学生工具），废弃旧 OSS 路线。
- 旧 OSS 规划已归档至 `_archive_old_oss_plan/`，**不再参考**。
- 现有代码骨架（contracts / skills / pipeline / services / api）**保留**，将被改造为新架构中的"确定性 skill 执行核"。
- 下一步：按 [`ROADMAP.md`](./ROADMAP.md) 的 M1 接入 LangGraph。

---

## 阅读顺序（接手者 / Sonnet 4.6 看这里）

按顺序读：

1. [`VISION.md`](./VISION.md) — 北极星：项目身份、真实场景、与对手差异、三档目的地。
2. [`ARCHITECTURE.md`](./ARCHITECTURE.md) — 同心圆架构、LangGraph 节点图、八层职责、契约定义、降级策略。**所有代码必须能追溯到这里**。
3. [`ROADMAP.md`](./ROADMAP.md) — M0→M6 分阶段施工清单，每阶段有出口标准。
4. [`SKILL_PLAYBOOK.md`](./SKILL_PLAYBOOK.md) — 怎么写一个 skill（deterministic / llm / hybrid 三型），含模板。
5. [`FRONTEND.md`](./FRONTEND.md) — 前端是笔记本式、一页一题、KaTeX 渲染、Word/PDF 导出，沿用 Luminous Minimalist 设计系统。
6. [`CONVENTIONS.md`](./CONVENTIONS.md) — 代码规约、命名、日志、红线速查。
7. [`BACKLOG.md`](./BACKLOG.md) — 颗粒化任务卡，可直接领。

---

## 一句话哲学

- **太阳是 Solve Contract**：8 字段契约，所有层围绕它旋转。
- **行星是学科**（机械系优先：高数 / 大学物理 / 工程力学 / 机械原理 / 公差测量 / 汽车理论）。
- **卫星是题型 skill**：每颗卫星是一个独立模块，遵守 Protocol，脱壳可跑。
- **Agent 只是分发器**：LangGraph 中的 router 节点只查表调用 skill，**业务逻辑零落在 graph 里**。
- **诚实降级**：图像视觉推理只能上云；无网时返回"图像理解需联网，已为你提取文字部分"，不假装能做。

---

## 本地运行（M1 完成前的状态）

```bash
# 安装
uv sync --extra dev

# 跑测试
uv run pytest

# 跑一道题（不经 HTTP）
python scripts/smoke.py "求 x^2 对 x 的导数"

# 启 HTTP
uv run uvicorn examsolver.api.app:app --reload
```

本机 LLM（Gemma 4，几天后换 GPT-OSS）：

```powershell
.\scripts\start-examsolver-with-gemma.ps1
```

云端 LLM（Claude Sonnet 4.6）需要 `ANTHROPIC_API_KEY` 环境变量（M1 起接入）。

---

## 技术栈（B 路线确认）

| 维度 | 选型 |
|---|---|
| 编排 | LangGraph (Python) |
| LLM 主力 | Claude Sonnet 4.6（云）|
| LLM 本地 | Gemma 4 → 几天后换 GPT-OSS |
| VLM | Claude 4.6 多模态（仅云端，无本地替代）|
| OCR | PaddleOCR（本地、中文友好、识公式）|
| Embedding | sentence-transformers（本地）|
| 向量库 | sqlite-vec（与现有 SQLite 同文件）|
| Web 框架 | FastAPI |
| 前端 | Next.js 15 + React 19（抢救 `D:\codex file\ExamSolver`）|
| 设计系统 | Luminous Minimalist（沿用旧版 DESIGN.md）|
| 导出 | python-docx + 浏览器 print-to-PDF |

---

*文档版本：v1.0（B 路线首版重写，2026-05）*
