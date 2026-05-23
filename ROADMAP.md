# Examsolver · 施工路线图 v1.0（B 路线）

> 本文档是给 Sonnet 4.6 接手的**分阶段施工清单**。每个 milestone 有：目标、范围、出口标准、关键文件、风险。**先完成出口标准再进下一阶段**。

---

## 阶段总览

| M | 名称 | 估时（全职日）| 出口一句话 |
|---|---|---|---|
| M0 | 文档对齐 + 现状盘点 | 0.5 | 8 份文档就位、依赖清单确认、旧代码改造范围确定 |
| M1 | LangGraph 接入 + Router | 3-5 | smoke 一道题走完 graph，router_agent 能判 subject+type |
| M2 | LLM 抽象 + 第一颗 LLM skill | 3 | `calculus.derivative` 升级为 hybrid（旧 sympy + LLM 解释），加 `general.cot_with_textbook` |
| M3 | OCR + RAG + 公差行星 | 5-7 | 用户能上传公差教材，问"H 和 h 区别"得带教材引用的答案 |
| M4 | 前端 + 一页一题 + Word 导出 | 5-7 | 浏览器打开 → 输入题 → 笔记页 → 导出 docx |
| M5 | VLM + 机械原理行星 + 错题本 + 卡片 | 7-10 | 拍齿轮图 → 算传动比 → 加错题本 → 生成 3 张卡片 |
| M6 | 演示打磨 + 答辩材料 + 部署 | 3-5 | demo.gif < 3min + 公开链接 + interview-talk-track.md |

**总估时**：26-37 全职日 ≈ 6-8 周。

---

## M0 · 文档对齐 + 现状盘点（0.5 日）

### 目标
保证 Sonnet 4.6 接手时知道方向、知道现状、知道改什么。

### 范围
1. 阅读全部 8 份新文档（≤ 1h）
2. 跑通现有测试：`uv run pytest` 全绿
3. 跑通现有 smoke：`python scripts/smoke.py "求 x^2 对 x 的导数"`
4. 确认依赖清单（[`pyproject.toml`](pyproject.toml)）需要新增：
   ```
   langgraph
   langchain-anthropic
   anthropic
   openai                     # 用于 llama-server 兼容 client
   paddleocr
   paddlepaddle
   sentence-transformers
   sqlite-vec
   python-docx
   pypdf
   pillow
   ```
5. 写一个 [`docs/data-flow.md`](docs/data-flow.md)：用现有代码画一遍当前调用链（理解 baseline）

### 出口标准
- [x] 现有 `pytest` 全绿
- [x] 现有 smoke 跑通
- [x] [`docs/data-flow.md`](docs/data-flow.md) 完成
- [x] [`pyproject.toml`](pyproject.toml) 新依赖加上并 `uv lock` 通过

### 关键文件
- 所有 `.md`
- `pyproject.toml`
- `uv.lock`

### 风险
- PaddleOCR + paddlepaddle 在 Windows 上安装可能踩坑 → 备选 `rapidocr-onnxruntime`（更轻）
- sqlite-vec 需要 Python 3.11+ 与 sqlite ≥ 3.41 → 检查 `sqlite3.sqlite_version`

---

## M1 · LangGraph 接入 + Router（3-5 日）

### 目标
用 LangGraph 重写 `solve_service.solve()`，新增 `router_agent` 节点。**功能等价于现状**，但走 graph。

### 任务
1. **建 `graph/` 包**
   - `state.py`：定义 `SolveState: TypedDict`
   - `nodes.py`：每个节点一个函数 `def xxx_node(state: SolveState) -> SolveState`
   - `build.py`：`build_graph() -> CompiledGraph`
2. **节点最小实现**（M1 只接旧节点，多模态/RAG 节点先空跑）
   - `normalize_node` ← 包装旧 [`normalizer.normalize`](src/examsolver/pipeline/normalizer.py)
   - `router_agent_node` ← M1 用旧 [`classifier.classify`](src/examsolver/pipeline/classifier.py) 兜底（LLM 路由放 M2）
   - `skill_node` ← 调旧 [`dispatcher.dispatch_or_unknown`](src/examsolver/pipeline/dispatcher.py)
   - `explanation_enhancer_node` ← 包装旧 [`services/explanation.py`](src/examsolver/services/explanation.py)
   - `format_node` ← 包装旧 [`formatter.format_response`](src/examsolver/pipeline/formatter.py)
   - `persist_node` ← 包装旧 [`storage/history_repo.py`](src/examsolver/storage/history_repo.py)
3. **改造 `services/solve_service.solve()`**
   - 内部从直接调用改为 `graph.invoke(initial_state)`
   - 外部签名不变（保持向后兼容）
4. **加扩契约**
   - [`contracts/solve.py`](src/examsolver/contracts/solve.py) 加 `Step` / `Citation` 数据类
   - `SolveRequest` 加 `image_paths: list[str] = []`（M3 才用到，先占位）
5. **测试**
   - `tests/graph/test_build.py`：`build_graph()` 不抛
   - `tests/graph/test_invoke.py`：跑一道导数题，response 与旧 service 输出等价
   - 所有旧 `tests/` 仍绿

### 出口标准
- [x] `python scripts/smoke.py "求 x^2 对 x 的导数"` 输出合法 SolveResponse
- [x] `GET /solve` 行为不变
- [x] 旧测试全绿
- [x] `tests/graph/` 新测试全绿
- [x] 日志中能看到 `[<rid>] INFO graph.normalize_node: ...` 形态

### 关键文件
- `src/examsolver/graph/*`
- `src/examsolver/services/solve_service.py`
- `src/examsolver/contracts/solve.py`

### 风险
- LangGraph 的 state merge 语义需要查文档；推荐用 `Annotated[list, operator.add]` 处理 list 字段
- 旧 service 的同步流被 graph 包装后 latency 应该差异 < 5%

---

## M2 · LLM 抽象 + 第一颗 LLM skill（3 日）

### 目标
- 抽象 `LLMClient` Protocol，支持云（Claude）和本地（Gemma 4 / GPT-OSS via llama-server）
- 让 `router_agent_node` 走真 LLM
- 加 `general.cot_with_textbook` 兜底 skill

### 任务
1. **`llm/` 包**
   - `base.py`：`LLMClient` Protocol + `Message` 数据类
   - `claude_client.py`：Anthropic API 封装
   - `local_gguf.py`：OpenAI 兼容 client 指向 `http://127.0.0.1:8080/v1`
   - `router.py`：`pick_llm(task_kind, needs_vision) -> LLMClient`
   - 测试用 `FakeLLM` 注入
2. **`graph/router_agent.py`**
   - prompt 模板：返回 JSON `{subject, question_type, confidence, reasoning}`
   - 先走旧 regex classifier（快、准时直接用）
   - 不命中或置信度 < 0.7 才调 LLM
   - 输出写回 `SolveState`
3. **新 skill：`skills/general/cot_with_textbook.py`**
   - 类型：Type-L
   - 兜底：subject 是 "general" 或所有 skill 不命中时走这条
   - prompt：让 LLM 按"思路 / 步骤 / 答案 / 易错点"结构化输出
   - 输出走 JSON schema 校验
4. **registry 升级**
   - `skills/registry.py` 自动发现 `skills/<subject>/*.py`
   - 维护 `(subject, question_type) -> Skill` 映射
   - 提供 `get_skill(subject, question_type) -> Skill | None`

### 出口标准
- [ ] `python scripts/smoke.py "汽车 ABS 系统起到什么作用？"` 走 general skill 返回结构化笔记
- [ ] 设环境变量切到本地 LLM 后，路由结果与云端 ≥ 80% 一致（小规模 10 条手测）
- [ ] `tests/llm/` 用 FakeLLM 覆盖关键路径

### 关键文件
- `src/examsolver/llm/*`
- `src/examsolver/graph/router_agent.py`
- `src/examsolver/skills/general/cot_with_textbook.py`
- `src/examsolver/skills/registry.py`

### 风险
- 本地 LLM JSON 输出不稳 → 加 `json_schema` 强约束 + 重试 1 次
- Claude API 速率限制 → 测试用 FakeLLM，dev 用本地

---

## M3 · OCR + RAG + 公差行星（5-7 日）

### 目标
- PaddleOCR 跑通
- sqlite-vec 索引 1 本公差教材
- 新行星 `tolerance/` 含 1 颗卫星 `fit_type`
- 用户问"H 和 h 区别"得到带教材引用的答案

### 任务
1. **`multimodal/ocr_paddle.py`**
   - 单例 OCR 引擎（首次加载 ~5s）
   - 输入 image_paths，输出 OCRResult
   - 失败抛 `OCRError`，graph 标记继续
2. **`graph/nodes.ocr_node`**
   - state 有 image_paths 才执行
   - 结果写 `state.ocr_text` `state.ocr_bboxes`
3. **`rag/` 包**
   - `chunker.py`：500 字 / 100 字重叠
   - `embedder.py`：sentence-transformers `paraphrase-multilingual-MiniLM-L12-v2`（384 维，中文友好）
   - `store_sqlite_vec.py`：建表 + 写入
   - `retriever.py`：top_k 检索
4. **`scripts/index_textbook.py`**
   - 入参：`<pdf_path> --subject tolerance --title "公差与测量"`
   - 流程：pypdf 读 → 失败回退 PaddleOCR → chunk → embed → 写库
5. **`storage/documents_repo.py`**
   - documents 表 CRUD
6. **新行星 `skills/tolerance/`**
   - `_meta.py`：subject="tolerance", display_name="公差与测量"
   - `fit_type.py`：Type-H
     - `needs_rag=True`
     - 流程：RAG 检索 → LLM 抽符号（H/h/+0.025/...）→ 查表（内置 ISO 286 简表）→ LLM 解释 → 引用教材片段
7. **`graph/nodes.rag_retrieve_node`**
   - state.subject 对应行星有教材时执行
   - 结果写 `state.retrieved_chunks`
8. **API**
   - `api/routes/library.py`：`POST /library/upload` `POST /library/index/{doc_id}` `GET /library`

### 出口标准
- [ ] `python scripts/index_textbook.py data/textbooks/tolerance.pdf --subject tolerance` 跑通，索引 ≥ 50 chunks
- [ ] `python scripts/smoke.py "H7/g6 是什么配合？"` 返回的 SolveResponse.note.citations 至少 1 条指向教材
- [ ] OCR 处理一张含手写公式的图片 < 3s
- [ ] `tests/rag/test_retriever.py` 覆盖 happy path + empty result

### 关键文件
- `src/examsolver/multimodal/ocr_paddle.py`
- `src/examsolver/rag/*`
- `src/examsolver/skills/tolerance/*`
- `scripts/index_textbook.py`

### 风险
- 用户没有公差教材 PDF → 用工程力学或机械原理代替，重点是流程通
- PaddleOCR 模型首次下载 ~200MB → 文档说明，预下载脚本
- sentence-transformers 首次下载模型 ~500MB → 同上

---

## M4 · 前端 + 一页一题 + Word 导出（5-7 日）

### 目标
浏览器打开 → 输入题 → 看笔记 → 导出 docx。前端从 [`D:\codex file\ExamSolver`](D:/codex%20file/ExamSolver) 抢救，沿用 Luminous Minimalist 设计系统。

### 任务
1. **`frontend/` 初始化**
   - 复制 `D:\codex file\ExamSolver` 的 `app/` `components/` `lib/` 到 `frontend/`
   - 删除旧的 better-sqlite3、docx npm 依赖（导出走后端）
   - 保留 katex、Next.js 15、React 19
2. **路由**
   - `/` 主工作台：输入框 + 上传图 + 提交
   - `/note/[solve_id]`：一页一题视图
   - `/history`：列表
   - `/library`：教材上传管理
3. **`/note/[solve_id]` 视图**
   - 题目（KaTeX 渲染）
   - 思路一句话
   - 步骤列表（每步 description + formula_latex）
   - 答案块
   - 学生友好解释
   - 易错点 chips
   - 公式卡侧栏
   - 引用脚注（如有）
   - 顶部工具栏：导出 docx / 加入错题本 / 删除
4. **API 桥**
   - `frontend/lib/api.ts`：fetch `/solve` `/export/docx/{solve_id}` 等
5. **后端 docx 导出**
   - `export/docx_export.py`：python-docx + OMML 公式
   - `api/routes/export.py`：`GET /export/docx/{solve_id}` 返回流
6. **PDF 导出**
   - 走浏览器自带 `window.print()` + print stylesheet
   - 不再依赖后端 wkhtmltopdf / weasyprint

### 出口标准
- [ ] `pnpm dev` 起前端，`uv run uvicorn ...` 起后端，从 `localhost:3000` 解一道题完整跑通
- [ ] 导出的 docx 在 Word 2016+ 打开，公式以 OMML 显示（不是图片）
- [ ] `window.print()` 出来的 PDF 一页一题、KaTeX 公式不糊
- [ ] 设计风格保持 Luminous Minimalist（无 1px 边框、玻璃层级）

### 关键文件
- `frontend/**`
- `src/examsolver/export/docx_export.py`
- `src/examsolver/api/routes/export.py`
- `src/examsolver/api/routes/notes.py`

### 风险
- KaTeX 在 docx 里渲染：OMML 转换可能丢精度 → 简单公式直接用 OMML，复杂公式回退为图片
- Next.js 15 + React 19 服务端组件踩坑 → 复杂交互页用 "use client"

---

## M5 · VLM + 机械原理行星 + 错题本 + 卡片（7-10 日）

### 目标
- 接 Claude 4.6 多模态做视觉理解
- 新行星 `mechanism/` 含 `gear_train` Type-H skill
- 错题本完整闭环
- 自动生成 flashcard

### 任务
1. **`multimodal/vlm_claude.py`**
   - Claude Sonnet 4.6 messages API with image
   - 输入 image bytes + prompt
   - 输出自然语言描述
2. **`multimodal/fallback.py`**
   - 检测 Claude API 可达性（HEAD https://api.anthropic.com 超时 2s）
   - 不可达时 vlm 调用返回空 + fallback_reasons
3. **`graph/nodes.vlm_node`**
   - 仅当 `state.needs_vision=True` 且 image 存在时跑
   - router_agent 改造为：图像存在 + 题目含视觉关键词 → 设 needs_vision=True
4. **新行星 `skills/mechanism/`**
   - `gear_train.py`：Type-H
     - `needs_vision=True`
     - 流程：VLM 描述 → LLM 抽齿数 → 算传动比 → LLM 解释
   - `crank_slider.py`：Type-L（先纯文本，v1.5 加视觉）
5. **错题本**
   - `storage/mistakes_repo.py`：CRUD
   - `api/routes/mistakes.py`：POST 加入 / GET 列表 / DELETE / POST 批量导出
   - 前端 `/mistakes`：分组、筛选、批量导出
6. **Flashcard**
   - `notes/flashcard.py`：从 NoteEntry 抽 3 类卡（公式 / 概念 / 易错）
   - 在 `note_builder_node` 里调用
   - 前端 `/flashcards`：抽认卡 UI（spacebar 翻面 + 左右键切换）

### 出口标准
- [ ] 上传一张齿轮传动图 + "传动比是多少？" → 返回正确传动比 + 步骤 + 重绘图（v1.5 再说）
- [ ] 拔网线后同样请求返回 "图像理解需联网，已为你提取文字部分"
- [ ] 任意笔记可一键加入错题本，错题本可批量导出 docx
- [ ] 任意笔记自动生成 ≥ 2 张 flashcard

### 关键文件
- `src/examsolver/multimodal/vlm_claude.py`
- `src/examsolver/multimodal/fallback.py`
- `src/examsolver/skills/mechanism/*`
- `src/examsolver/notes/flashcard.py`
- `frontend/app/mistakes/**`
- `frontend/app/flashcards/**`

### 风险
- Claude 多模态成本：≈ $0.003/image，需提醒用户配额
- 视觉理解准确度：齿轮图相对友好，复杂机构（曲柄连杆）准确率低 → v1.0 只承诺齿轮

---

## M6 · 演示打磨 + 答辩材料 + 部署（3-5 日）

### 目标
能投简历、能讲 30 分钟、能给面试官现场点链接看。

### 任务
1. **demo 视频**
   - 录 < 3 分钟 gif，4 个场景：
     1. 高数解题 + 导出 docx
     2. 公差教材上传 + 引用回答
     3. 齿轮图上传 + 传动比
     4. 错题本 + flashcard 速过
   - 工具：ScreenToGif（Windows）
   - 放 `docs/demo.gif`
2. **架构图**
   - 用 [Excalidraw](https://excalidraw.com/) 画同心圆 + LangGraph 节点图
   - 导出 PNG 到 `docs/architecture.png`
   - 在 README 顶部嵌入
3. **答辩话术**
   - `docs/interview-talk-track.md`：STAR 格式
     - Situation：大学生痛点
     - Task：做一个能用的、能讲清的项目
     - Action：架构选择 + 难点
     - Result：v1.0 数字 + demo
   - 准备 5 个常问问题的答案：
     1. 为什么 LangGraph？
     2. 怎么扩新学科？
     3. 多模态怎么降级？
     4. 与 ChatGPT 区别？
     5. 商业化怎么想？
4. **部署**
   - 后端：Render / Fly.io 跑 FastAPI + SQLite
   - 前端：Vercel
   - 限制：LLM 走 Claude API（demo 期自付费），本地 LLM 不上云
   - 写一个 `docs/deployment.md`
5. **README 美化**
   - 顶部 4 个 badges（Python / Node / License / Deployed）
   - 一张架构图
   - 3 个 quick start 段（一句话 / 30 秒 / 完整）
   - demo gif

### 出口标准
- [ ] `docs/demo.gif` < 3 分钟，4 场景齐
- [ ] `docs/architecture.png` 清晰，能放简历
- [ ] `docs/interview-talk-track.md` 写完
- [ ] 公开链接 1 个，能从 0 跑通一道题
- [ ] README 看起来不像玩具
- [ ] 简历能加一行 + 投递

### 关键文件
- `docs/demo.gif`
- `docs/architecture.png`
- `docs/interview-talk-track.md`
- `docs/deployment.md`
- `README.md`

### 风险
- 部署上 LLM 配额烧钱 → demo 期开启用户认证（password gate）
- 视频太长面试官不看 → 严格 3 分钟内，每场景 45 秒

---

## 横切关注（每个 M 都要做）

### 测试
- 任何新文件配镜像测试文件
- 任何新契约改动加契约形状测试
- 覆盖率不强求，但 happy path 必有

### 日志
- 每个新 graph node 加 INFO 入口出口
- 每个 LLM call 加 INFO（task_kind, model, tokens_in, tokens_out）

### 文档
- 完成一个 M 在 README 写一段 "本周做了什么"
- ARCHITECTURE / CONVENTIONS / SKILL_PLAYBOOK 有偏离时同步改

### 提交
- 单人推 main 即可
- commit 前跑 `pytest` `ruff check` `mypy`

---

## 不在路线图里的事（明确缓办）

| 项 | 推到哪里 |
|---|---|
| 用户登录 / 多租户 | v2.0 |
| 移动端原生 | 永不 |
| 题库 / 分享 | v2.0 |
| 全自动机构图重绘 | v1.5 选做 |
| 实时协作 | 永不 |
| 自训模型 | 永不 |
| Discord / 社区运营 | 永不 |
| 非机械系学科批量扩展 | 视精力 |

---

## 进度自检

每完成一个 M，回答：

1. 出口标准全部勾上了吗？
2. ARCHITECTURE / CONVENTIONS 有需要同步改的吗？
3. 这一阶段写的代码里有违反红线（§13）的吗？
4. 我现在能给面试官讲清这一阶段的工程价值吗？

四个都通过才进下一 M。

---

*文档状态：v1.0 初稿。B 路线首版。任何 M 实施中发现路线问题，先更新本文件再写代码。*
