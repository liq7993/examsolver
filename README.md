# Examsolver

> 大学生期末突击复习助手 · 确定性解题内核 + LangGraph 编排 + 多模态降级 · 面试主作品

**这是什么**：把一道题变成一页可复用的解题笔记的工具——确定性内核（sympy）给出可验证的答案与步骤，云端大模型补「学生解释」与突击复习卡，机械图理解走云端 VLM，公差等题型附教材引用。一题一页，可导出 Markdown / PDF，错题自动归档。机械系优先覆盖，其他学科按需扩展。

**它不是**：搜题软件、AI 套壳问答、通用 GPT 客户端。答案由确定性内核计算，**不靠大模型猜**；抽取/解析失败宁可触发兜底也**绝不编造**。

---

## 当前状态（2026-06）

- **可用产品形态**：后端 FastAPI 自带的单页工作台（`/` 直接服务 `api/static/index.html`），含侧边栏「设置 / 错题本」、设置弹窗（选云端服务商 + 填 API key）、解题工作区、Markdown/PDF 导出、KaTeX 公式渲染。**打开 `http://localhost:8000/` 即用。**
- **LLM 方向**：聚焦闭源云模型（MiniMax / Claude / DeepSeek / Moonshot / OpenAI，统一 OpenAI 兼容接口），本地 GGUF（Gemma / GPT-OSS）为可选离线后端。
- **质量基线**：`290 passed / 3 skipped`，`ruff` + `mypy --strict` 全绿；测试含离线 golden-set 回归与教材引用命中用例，FakeLLM 注入保证可离线复跑。
- **多步解题（agentic）**：二阶/三阶导、矩阵连乘等多步题由 agentic 环编排——识别题型后**确定性拆解**成子步、逐步调确定性 skill 求解并验算、链式拼装。评测台实测：同一 MiniMax 模型，raw 60% → 接入内核 100%（多步 Δ=+40%，大于单步的 +17%），且 token 更省（≈846 vs 4399）。
- 早期的独立 Next.js 前端构建已移除——产品前端就是上面的 `:8000` 内置 UI。

---

## 架构：同心圆 + LangGraph

- **太阳 = Solve Contract**：统一的请求/结果契约，所有层围绕它旋转。
- **行星 = 学科**：高数 / 大学物理 / 工程力学 / 机械原理 / 公差测量 / 汽车理论，`general` 兜底。
- **卫星 = 题型 skill**：每个 skill 是独立模块，遵守 Protocol、**脱壳可跑**（不 import langgraph/fastapi/其他 skill）。三型：确定性 / 纯 LLM / 混合（主力混合）。
- **Agent 只分发**：LangGraph 的 `router_agent` 节点只查表选 skill，**业务逻辑零落在 graph 里**。

**管线节点**（单一职责，按题型条件跳过）：

```
normalize → ocr → vlm → router_agent → rag_retrieve → skill / general / agentic
          → explanation_enhancer → plot → note_builder → format → persist
```

- `skill_node` 跑确定性解题（sympy），`general_node` 走结构化兜底，`agentic` 跑多步编排环；
- `explanation_enhancer` 补教学性「学生解释」，`plot_node` 用 sympy 确定性生成函数图像；
- `note_builder` 组装一页笔记，`persist` 落 SQLite。

> 节点图与契约字段以 [`ARCHITECTURE.md`](./ARCHITECTURE.md) 为准——所有代码都应能追溯到那里。

---

## 关键能力

| 能力 | 怎么做 |
|---|---|
| **确定性解题** | sympy 求导 / 矩阵 / 受力平衡等；答案与步骤可验证，**不让大模型编答案**。Type-D 数学题禁用正则解析表达式（正则只用于自然语言抽取）。|
| **多步解题（agentic）** | 二阶/三阶导、矩阵连乘等：识别题型后**确定性拆解**为子步，逐步调用确定性 skill 求解＋验算，链式拼装；只有未识别的新型多步才回退 LLM 规划。拆解与计算都确定性，弱模型也不易出错。|
| **学生解释** | 云端大模型生成讲解/直觉/常见错误/自检问题，作为教学层包裹确定性答案。|
| **多模态 + 诚实降级** | PaddleOCR 本地识字；看图（齿轮图算传动比等）走云端 Claude VLM。**离线时返回「图像理解需联网，已为你提取文字部分」，不假装本地能看图。** |
| **RAG + 教材引用** | sentence-transformers 嵌入 + sqlite-vec 检索；公差题（H7/g6 等）附教材引用片段。|
| **错题本** | 笔记页一键加入错题，按学科归档，支持复习打卡与 Markdown 导出。|
| **突击复习卡** | 从每页笔记抽 3 类卡（公式 / 概念 / 易错）。**后台异步生成**——`/solve` 不等卡（实测 ~0.07s 返回），卡片在后台跑完落库，下次查看即就绪。|
| **导出** | 一页笔记导出 Markdown / PDF。|

---

## LLM 接入

- **统一接口**：`llm/router.py:pick_llm(task_kind, needs_vision)` 按任务选后端；云端走 `OpenAICompatibleClient`（Bearer 鉴权），Claude 走专用客户端，本地走 `LocalGGUFClient`（llama-server，无 key）。
- **运行时设置**：在 `:8000` 设置弹窗选服务商 + 填 key，存到 gitignored 的 `data/runtime_settings.json`，启动时由 `apply_to_environ` 投影进 `os.environ`，改完即生效、重启仍在。key 只存本机、界面只显示末四位、**绝不日志**。
- **MiniMax 兼容修正**：MiniMax 会把 json_schema 结果包在 `structured_output` 外壳里，客户端会自动解包，使结构化输出（复习卡 / 解释）在各服务商间一致。
- **确定性优先**：求导/矩阵/受力平衡等**无需联网、无需 key、永远免费**；云模型只负责讲解与卡片。

---

## 本地运行（WSL）

```bash
# 安装依赖（uv 管理）
uv sync --extra dev

# 跑测试 / 静态检查
.venv/bin/python -m pytest -q
.venv/bin/ruff check src tests
.venv/bin/mypy src

# 起服务，然后浏览器打开 http://localhost:8000/
.venv/bin/python -m uvicorn examsolver.api.app:app --host 127.0.0.1 --port 8000

# 不经 HTTP 跑一道题
.venv/bin/python scripts/smoke.py "求 x^2 对 x 的导数"
```

- **云端解释 / 复习卡**：在 `:8000` 的「设置」里选服务商并粘贴 API key 即可（题目会发往该服务商，请勿提交隐私内容并设置消费上限）。
- **本地 GGUF（可选离线）**：preset 由 `EXAMSOLVER_LLM_PRESET=gemma4|gpt-oss-20b` 切换，详见 [`docs/gpt-oss-setup.md`](./docs/gpt-oss-setup.md)。

---

## 技术栈

| 维度 | 选型 |
|---|---|
| 编排 | LangGraph (Python) |
| Web / 服务化 | FastAPI（`/solve`、历史、错题、资料索引、导出、运行时设置）|
| 产品前端 | FastAPI 服务的单页工作台（`api/static`，原生 JS + KaTeX）|
| 确定性内核 | sympy（求解 + 函数绘图）|
| 云端 LLM | OpenAI 兼容（MiniMax / DeepSeek / Moonshot / OpenAI）+ Claude；统一接口 + 运行时切换 |
| 本地 LLM | Gemma 4 / GPT-OSS（GGUF，llama-server，可选）|
| VLM | Claude 多模态（仅云端，离线诚实降级）|
| OCR | PaddleOCR（本地、中文与公式友好）|
| 检索 | sentence-transformers 嵌入 + sqlite-vec |
| 存储 | SQLite（解题历史 / 错题 / 资料分块 + 向量）|
| 导出 | Markdown / PDF |

---

## 仓库导航

| 文档 | 内容 |
|---|---|
| [`VISION.md`](./VISION.md) | 项目身份、真实场景、与对手差异、目标分档 |
| [`ARCHITECTURE.md`](./ARCHITECTURE.md) | 同心圆架构、LangGraph 节点图、契约、降级策略（**代码以此为准**）|
| [`ROADMAP.md`](./ROADMAP.md) | M0→M6 分阶段清单（现作参考，非硬验收门）|
| [`SKILL_PLAYBOOK.md`](./SKILL_PLAYBOOK.md) | 如何写一个 skill（三型 + 模板）|
| [`CONVENTIONS.md`](./CONVENTIONS.md) | 代码规约、命名、日志、红线速查 |
| [`BACKLOG.md`](./BACKLOG.md) | 颗粒化任务卡 |

代码：`src/examsolver/{contracts,skills,pipeline,graph,llm,multimodal,notes,storage,services,api}`；测试在 `tests/`。

---

## 设计红线

- **绝不编造**：抽取/解析失败 → `raise SkillExecutionError` 触发兜底，不给默认假答案。
- **诚实降级**：能力受限（如离线看图）如实告知，不假装。
- **确定性可验证**：数学题用 sympy，不用正则解析表达式；函数绘图也走 sympy。
- **skill 解耦**：skill 不依赖框架与彼此，可单测、脱壳可跑。
- **不泄密**：API key / 完整 prompt 不进日志。

---

*文档版本：v2.0（2026-06，反映 M5 完成态与 `:8000` 产品前端）*
