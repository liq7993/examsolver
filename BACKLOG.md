# 任务卡 BACKLOG v1.0（B 路线）

> 颗粒化任务，可直接领。每张卡包含：编号 / 标题 / 所属 M / 估时 / 出口 / 涉及文件 / 前置依赖。
>
> 阅读顺序：先 [`ROADMAP.md`](./ROADMAP.md) 看大方向，再来这里挑卡做。

---

## 卡片状态约定

- `📥 TODO` 未开始
- `🚧 DOING` 进行中（同时 ≤ 1 张）
- `✅ DONE` 完成
- `⏸ BLOCKED` 卡住（注明原因）

完成一张卡：勾掉清单、改状态、commit + 短描述。

---

## M0 · 文档对齐 + 现状盘点

### ✅ M0-01 · 跑通现有测试与 smoke 基线
**估时**：30 min
**前置**：无
**出口**：
- [x] `uv sync --extra dev` 装齐依赖
- [x] `uv run pytest` 全绿（71 passed）
- [x] `python scripts/smoke.py "求 x^2 对 x 的导数"` 输出合法 JSON
  - 当前 shell 无裸 `python` 命令，实际用 `uv run python scripts/smoke.py "求 x^2 对 x 的导数"` 验证通过。
- [x] 截图记录 baseline 到 `docs/baseline-screenshot.png`

### ✅ M0-02 · 新增依赖入 pyproject
**估时**：30 min
**前置**：M0-01
**出口**：
- [x] 在 [`pyproject.toml`](pyproject.toml) `dependencies` 加：
  ```
  langgraph
  anthropic
  openai
  paddleocr
  paddlepaddle
  sentence-transformers
  sqlite-vec
  python-docx
  pypdf
  pillow
  httpx
  ```
- [x] `uv lock` 不抛错（Resolved 135 packages）
- [x] `uv sync` 装齐
  - 默认同步会移除 dev 依赖；已额外执行 `uv sync --extra dev` 恢复 pytest/ruff/mypy。
  - 依赖导入检查通过。
- [x] 已知问题（Windows + paddlepaddle 版本）记录到 `docs/troubleshooting.md`

### ✅ M0-03 · 画 baseline 数据流图
**估时**：1 h
**前置**：M0-01
**出口**：
- [x] 新建 [`docs/data-flow.md`](docs/data-flow.md)
- [x] 用 mermaid 画当前 `solve_service.solve()` 的完整调用链
- [x] 标出哪些会被 M1 改造、哪些保留

---

## ✅ M1 · LangGraph 接入 + Router

### ✅ M1-01 · 建 `graph/` 包骨架
**估时**：1 h
**前置**：M0-02
**出口**：
- [x] 新建 `src/examsolver/graph/{__init__.py,state.py,nodes.py,build.py}`
- [x] `state.py` 定义 `SolveState: TypedDict` 含 §ARCHITECTURE 2.3 全部字段
- [x] `build.py` 暴露 `build_graph() -> CompiledStateGraph` 占位
- [x] `tests/graph/test_state.py` 验证字段齐

### ✅ M1-02 · 扩契约：Step / Citation / image_paths
**估时**：1 h
**前置**：M0-02
**出口**：
- [x] [`contracts/solve.py`](src/examsolver/contracts/solve.py) 加 `Step` `Citation`
- [x] `SolveRequest` 加 `image_paths: list[str] = []`
- [x] `SolveResult.steps` 从 `list[str]` 改为 `list[Step]`
- [x] 旧 skill 适配（`derivative` `matrix_mul` `force_balance`）
- [x] 旧测试更新通过（75 passed）
- [x] 契约形状测试 `tests/contracts/test_solve_contract_shape.py` 更新

### ✅ M1-03 · 实现 normalize_node + format_node + persist_node
**估时**：2 h
**前置**：M1-01, M1-02
**出口**：
- [x] `graph/nodes.py` 三个节点包装现有 [`normalizer.normalize`](src/examsolver/pipeline/normalizer.py) / [`formatter.format_response`](src/examsolver/pipeline/formatter.py) / [`history_repo.save_history`](src/examsolver/storage/history_repo.py)
- [x] 每个节点入口出口 INFO log
- [x] 单测 `tests/graph/test_nodes.py` 用 minimal state 验证字段写入

### ✅ M1-04 · 实现 router_agent_node（M1 用旧 classifier 兜底）
**估时**：2 h
**前置**：M1-03
**出口**：
- [x] `graph/router_agent.py` 内部调旧 [`classifier.classify`](src/examsolver/pipeline/classifier.py)
- [x] 写 state.subject / state.question_type / state.routing_confidence(=1.0 if rule hit)
- [x] LLM 路由占位（M2 才真接），目前 confidence < 0.5 → subject="general", type="unknown"
- [x] 单测覆盖 3 类旧题型 + 1 个 unknown

### ✅ M1-05 · 实现 skill_node + general_node
**估时**：2 h
**前置**：M1-04
**出口**：
- [x] `graph/nodes.py` 加 `skill_node`：查 registry 调 `Skill.solve()`，写 state.solve_result
- [x] `general_node` 占位返回固定 "unknown skill" SolveResult（M2 接真 LLM 后替换）
- [x] 失败时 append `state.fallback_reasons` + 转 general_node

### ✅ M1-06 · 接 explanation_enhancer_node
**估时**：1 h
**前置**：M1-05
**出口**：
- [x] 包装现有 [`services/explanation.py`](src/examsolver/services/explanation.py)
- [x] 节点判 `state.solve_result.student_explanation is None` 才执行
- [x] 写回 `state.solve_result`

### ✅ M1-07 · 接 note_builder_node（M1 最小版）
**估时**：2 h
**前置**：M1-06
**出口**：
- [x] 新建 `src/examsolver/notes/note_builder.py`
- [x] `build_note(solve_result, normalized) -> NoteEntry`，目前 `common_mistakes=[]` `flashcards=[]` `related_formulas=[]`（M5 再丰富）
- [x] `contracts/solve.py` 加 `NoteEntry`
- [x] `state.note` 写入

### ✅ M1-08 · build_graph 串起来 + solve_service 切换
**估时**：1.5 h
**前置**：M1-07
**出口**：
- [x] `build.py` 用 LangGraph DSL 连接节点（线性图，M1 暂无分支）
- [x] 改造 [`services/solve_service.solve()`](src/examsolver/services/solve_service.py) 内部调 `graph.invoke(initial_state)`
- [x] 外部签名不变
- [x] `python scripts/smoke.py "求 x^2 对 x 的导数"` 与改造前输出语义等价

### ✅ M1-09 · M1 出口验收
**估时**：1 h
**前置**：M1-01..M1-08
**出口**：
- [x] 所有旧测试绿
- [x] `tests/graph/` 全绿
- [x] 日志格式符合 [`CONVENTIONS §4.3`](./CONVENTIONS.md)
- [x] `POST /solve` HTTP 行为不变
- [x] commit `M1: langgraph integration complete`

---

## M2 · LLM 抽象 + 第一颗 LLM skill

### ✅ M2-01 · `llm/` 包骨架 + Protocol
**估时**：1 h
**前置**：M1-09
**出口**：
- [x] 新建 `src/examsolver/llm/{__init__.py,base.py,router.py}`
- [x] `base.py` 定义 `LLMClient` Protocol + `Message` 数据类
- [x] `router.py` 实现 `pick_llm(task_kind, needs_vision)`，目前返回 None（M2-02 / M2-03 填）

### ✅ M2-02 · Claude client
**估时**：2 h
**前置**：M2-01
**出口**：
- [x] `llm/claude_client.py` 实现 `LLMClient`
- [x] 支持 `json_schema` 强约束（用 Anthropic tool use）
- [x] 支持 `chat_with_image(images=[bytes])`
- [x] 失败重试 1 次
- [x] 单测用 `respx` mock httpx 请求

### ✅ M2-03 · Local GGUF client
**估时**：1.5 h
**前置**：M2-01
**出口**：
- [x] `llm/local_gguf.py` 走 OpenAI-compatible API（指 llama-server）
- [x] 配置读自 `EXAMSOLVER_LLM_BASE_URL` `EXAMSOLVER_LLM_MODEL`
- [x] JSON 输出用 grammar / json_schema_strict
- [x] 测试用本地起 llama-server（可标 `@pytest.mark.local`）

### ✅ M2-04 · FakeLLMClient（测试用）
**估时**：1 h
**前置**：M2-01
**出口**：
- [x] `tests/_helpers/fake_llm.py` 实现 `FakeLLMClient`
- [x] 行为：根据 (task_kind, prompt_hash) 返回预录响应
- [x] 工厂方法 `from_recorded(payload: str | dict) -> FakeLLMClient`

### ✅ M2-05 · router 真路由（含 LLM 兜底）
**估时**：2 h
**前置**：M2-02, M2-04
**出口**：
- [x] [`graph/router_agent.py`](src/examsolver/graph/router_agent.py) 改造：
  1. 先走 regex（旧逻辑）
  2. 不命中调 `llm.router.pick_llm("route", False)` 出 JSON
  3. LLM 也无法判 → general / unknown
- [x] `prompts/router_agent.zh.md` 写好
- [x] 单测用 FakeLLM 覆盖 3 条路径

### ✅ M2-06 · 新行星 `general/` + `cot_with_textbook` skill
**估时**：3 h
**前置**：M2-02
**出口**：
- [x] `skills/general/_meta.py`
- [x] `skills/general/cot_with_textbook.py`（Type-L）
- [x] `skills/general/prompts/cot_with_textbook.zh.md`
- [x] `tests/skills/general/test_cot.py` + 3 条 fixture
- [x] `python scripts/smoke.py "汽车 ABS 起到什么作用？"` 走 general 返回结构化笔记

### ✅ M2-07 · Skill registry 自动发现
**估时**：1.5 h
**前置**：M2-06
**出口**：
- [x] [`skills/registry.py`](src/examsolver/skills/registry.py) 扫描 `skills/<subject>/*.py` 找 Skill 子类
- [x] 提供 `get_skill(subject, question_type) -> Skill | None`
- [x] 启动时打印发现的 skill 列表（INFO log）
- [x] 单测覆盖

### 📥 M2-08 · M2 出口验收
**估时**：30 min
**前置**：M2-01..M2-07
**出口**：
- [ ] 路由准确率手测 ≥ 80%（10 条样本）
- [ ] 切本地 LLM 路由结果与云端 ≥ 80% 一致
- [ ] commit `M2: llm abstraction + general skill`

---

## M3 · OCR + RAG + 公差行星

### 📥 M3-01 · PaddleOCR 集成
**估时**：3 h
**前置**：M2-08
**出口**：
- [ ] `multimodal/ocr_paddle.py` 单例 + lazy load
- [ ] `OCRResult` 数据类
- [ ] 单测用一张测试图（中文 + 公式）
- [ ] 处理一张 1024×768 图 < 3s
- [ ] 失败抛 `OCRError`，文档说明 fallback

### 📥 M3-02 · `ocr_node` 集成进 graph
**估时**：1 h
**前置**：M3-01
**出口**：
- [ ] `graph/nodes.py` 加 `ocr_node`
- [ ] 仅 `state.image_paths` 非空时执行
- [ ] 失败 append fallback_reasons 继续
- [ ] `graph/build.py` 加条件边

### 📥 M3-03 · sentence-transformers embedder
**估时**：1.5 h
**前置**：M2-08
**出口**：
- [ ] `rag/embedder.py` 单例 + lazy load
- [ ] 默认模型 `paraphrase-multilingual-MiniLM-L12-v2`
- [ ] 接口：`embed(text: str) -> list[float]` / `embed_batch(texts) -> list[list[float]]`
- [ ] 单测 happy path + 维度断言

### 📥 M3-04 · sqlite-vec 向量存储
**估时**：2 h
**前置**：M3-03
**出口**：
- [ ] `rag/store_sqlite_vec.py` 建表 + 写入
- [ ] 与现有 SQLite 同文件
- [ ] `documents` 表 + `chunks` 表 + `chunk_vec` 虚表
- [ ] 单测覆盖建表 + 插入 + 检索

### 📥 M3-05 · Chunker
**估时**：1.5 h
**前置**：M3-04
**出口**：
- [ ] `rag/chunker.py`：500 字 + 100 字重叠
- [ ] 尊重段落 / 标题分隔
- [ ] 单测：长文本切分预期数 / 重叠量

### 📥 M3-06 · Retriever
**估时**：1.5 h
**前置**：M3-04
**出口**：
- [ ] `rag/retriever.py` `retrieve(query, subject, top_k=5) -> list[TextbookChunk]`
- [ ] cosine distance threshold 0.5
- [ ] 单测覆盖命中 / 不命中 / 跨学科隔离

### 📥 M3-07 · `index_textbook.py` 脚本
**估时**：2 h
**前置**：M3-05, M3-06, M3-01
**出口**：
- [ ] `scripts/index_textbook.py`
- [ ] 入参 `<pdf_path> --subject <s> --title <t>`
- [ ] 流程：pypdf 读 → 失败回退 PaddleOCR → chunk → embed → 写库
- [ ] 实测对一本 PDF 教材索引完成 ≥ 50 chunks

### 📥 M3-08 · 新行星 `tolerance/` + `fit_type` skill
**估时**：3 h
**前置**：M3-06
**出口**：
- [ ] `skills/tolerance/{_meta.py,_tables.py,fit_type.py}`
- [ ] `_tables.py` 内置 ISO 286 简表（基本偏差查表）
- [ ] `fit_type.py` Type-H，`needs_rag=True`
- [ ] prompt 模板 `prompts/fit_type_extract.zh.md`
- [ ] 5 条 fixture
- [ ] `python scripts/smoke.py "H7/g6 是什么配合？"` 走通

### 📥 M3-09 · `rag_retrieve_node` + Library API
**估时**：2 h
**前置**：M3-06, M3-08
**出口**：
- [ ] `graph/nodes.py` 加 `rag_retrieve_node`，按 `state.subject` 是否有教材决定
- [ ] `api/routes/library.py` 加 `GET /library` `POST /library/upload` `POST /library/index/{id}` `DELETE /library/{id}`
- [ ] `storage/documents_repo.py`

### 📥 M3-10 · M3 出口验收
**估时**：30 min
**前置**：M3-01..M3-09
**出口**：
- [ ] 用户能上传公差教材并索引
- [ ] "H7/g6 是什么配合？" 返回 citations ≥ 1
- [ ] commit `M3: ocr + rag + tolerance planet`

---

## M4 · 前端 + 一页一题 + Word 导出

### 📥 M4-01 · 前端骨架抢救
**估时**：2 h
**前置**：M3-10
**出口**：
- [ ] 从 [`D:\codex file\ExamSolver`](D:/codex%20file/ExamSolver) 复制 `app/` `components/` `lib/`（去掉 db / docx 相关）到 `examsolver/frontend/`
- [ ] `frontend/package.json` 保留 Next.js 15 / React 19 / KaTeX
- [ ] `pnpm install` 通过
- [ ] `pnpm dev` 起到 localhost:3000 不报错

### 📥 M4-02 · API 桥
**估时**：1.5 h
**前置**：M4-01
**出口**：
- [ ] `frontend/lib/api.ts`：fetch wrapper，base URL 走 env `NEXT_PUBLIC_API_BASE`
- [ ] `frontend/lib/types.ts`：与后端 NoteEntry / SolveResponse 类型一致
- [ ] 主页提交后能拿到 solve_id 跳转 `/note/[solve_id]`

### 📥 M4-03 · 主工作台 `/`
**估时**：2 h
**前置**：M4-02
**出口**：
- [ ] `app/page.tsx`：输入框 + 附图 + 学科 chip + 提交
- [ ] 提交中骨架屏
- [ ] 附图缩略图预览
- [ ] 设计走 Luminous Minimalist

### 📥 M4-04 · 一页一题 `/note/[solve_id]`
**估时**：4 h
**前置**：M4-02
**出口**：
- [ ] `app/note/[solve_id]/page.tsx`
- [ ] 题目 / 思路 / 步骤 / 答案 / 易错点 5 大区块
- [ ] 右侧公式速查 sticky 侧栏
- [ ] KaTeX 渲染（用 react-katex 或 ezpotato 等）
- [ ] 顶部工具栏：返回 / chip / 加错题 / 导出 docx / 打印

### 📥 M4-05 · 历史 `/history`
**估时**：1.5 h
**前置**：M4-02
**出口**：
- [ ] `app/history/page.tsx`
- [ ] 卡片列表（按时间倒序）
- [ ] subject chip 筛选
- [ ] 点击跳 note 页

### 📥 M4-06 · 后端 docx 导出
**估时**：3 h
**前置**：M3-10
**出口**：
- [ ] `export/docx_export.py`：python-docx + OMML（用 `lxml` 拼 OMML XML）
- [ ] `api/routes/export.py`：`GET /export/docx/{solve_id}` 返回流
- [ ] 导出文件名 `{subject}-{title}-{date}.docx`
- [ ] Word 2016+ 打开公式可编辑（不是图片）

### 📥 M4-07 · 浏览器 print → PDF
**估时**：1.5 h
**前置**：M4-04
**出口**：
- [ ] `app/globals.css` 加 `@media print` 规则
- [ ] sidebar / 顶栏 / 工具栏 `display: none`
- [ ] 一题一页 `page-break-after: always`
- [ ] KaTeX SVG 在打印中不糊

### 📥 M4-08 · M4 出口验收
**估时**：30 min
**前置**：M4-01..M4-07
**出口**：
- [ ] 端到端：浏览器解题 → 跳笔记页 → 导 docx → 打印
- [ ] 设计走 Luminous Minimalist 无明显偏差
- [ ] commit `M4: frontend + note page + export`

---

## M5 · VLM + 机械原理 + 错题本 + 卡片

### 📥 M5-01 · VLM Claude client
**估时**：2 h
**前置**：M4-08
**出口**：
- [ ] `multimodal/vlm_claude.py`：Claude Sonnet 4.6 多模态
- [ ] 输入 image bytes + prompt，输出 str
- [ ] 单测用 mock

### 📥 M5-02 · 离线降级检测
**估时**：1 h
**前置**：M5-01
**出口**：
- [ ] `multimodal/fallback.py`：`check_cloud_reachable() -> bool`
- [ ] 缓存 10s（避免每次解题都 ping）
- [ ] 单测覆盖在线 / 离线两态

### 📥 M5-03 · `vlm_node` + router needs_vision 判定
**估时**：2 h
**前置**：M5-01, M5-02
**出口**：
- [ ] `graph/nodes.py` 加 `vlm_node`
- [ ] router_agent 设 `state.needs_vision`：image_paths 非空 + 题目含视觉关键词
- [ ] 离线时 vlm_node 跳过，写 `state.fallback_reasons.append("vlm_offline")`

### 📥 M5-04 · 新行星 `mechanism/` + `gear_train` skill
**估时**：4 h
**前置**：M5-03
**出口**：
- [ ] `skills/mechanism/{_meta.py,gear_train.py,prompts/gear_train_extract.zh.md}`
- [ ] Type-H，needs_vision=True
- [ ] 5 条 fixture（含图片描述）
- [ ] 实测：上传一张齿轮图能返回正确传动比

### 📥 M5-05 · 错题本数据层 + API
**估时**：2 h
**前置**：M4-08
**出口**：
- [ ] `storage/mistakes_repo.py` + `mistakes` 表
- [ ] `api/routes/mistakes.py`：POST/GET/PATCH/DELETE + 批量导出
- [ ] 单测覆盖

### 📥 M5-06 · 错题本前端
**估时**：3 h
**前置**：M5-05
**出口**：
- [ ] `frontend/app/mistakes/page.tsx`（按学科分组）
- [ ] `frontend/app/mistakes/[subject]/page.tsx`
- [ ] 加批注 / 移除 / 批量导出
- [ ] 在 note 页"➕错题"按钮接通

### 📥 M5-07 · Flashcard 生成
**估时**：3 h
**前置**：M4-08
**出口**：
- [ ] `notes/flashcard.py`：从 NoteEntry 抽 3 类卡（公式 / 概念 / 易错）
- [ ] 在 `note_builder_node` 调用
- [ ] LLM prompt 模板 `notes/prompts/flashcard_extract.zh.md`
- [ ] 每个 note 至少出 2 张卡

### 📥 M5-08 · Flashcard 前端 + session
**估时**：3 h
**前置**：M5-07
**出口**：
- [ ] `frontend/app/flashcards/page.tsx` 卡片库
- [ ] `frontend/app/flashcards/session/[solve_id]/page.tsx` 抽认卡 UI
- [ ] 空格翻面、箭头切换 / 标会 / 标不会
- [ ] session 结束统计

### 📥 M5-09 · M5 出口验收
**估时**：30 min
**前置**：M5-01..M5-08
**出口**：
- [ ] 拍齿轮图 → 算传动比走通
- [ ] 拔网线后同请求返回降级提示
- [ ] 错题本闭环
- [ ] flashcard 自动生成 + session 可玩
- [ ] commit `M5: vlm + mechanism + mistakes + flashcards`

---

## M6 · 演示打磨 + 答辩 + 部署

### 📥 M6-01 · 录 demo gif
**估时**：3 h
**前置**：M5-09
**出口**：
- [ ] 用 ScreenToGif 录 4 场景 < 3 min 总长
- [ ] 落 `docs/demo.gif`

### 📥 M6-02 · 画架构图
**估时**：2 h
**前置**：M5-09
**出口**：
- [ ] Excalidraw 画同心圆 + LangGraph 节点图
- [ ] 导出 PNG 到 `docs/architecture.png`
- [ ] 嵌入 README

### 📥 M6-03 · 答辩话术
**估时**：3 h
**前置**：M5-09
**出口**：
- [ ] `docs/interview-talk-track.md`：STAR + 5 个 Q&A
- [ ] 5 个 Q：为什么 LangGraph / 怎么扩学科 / 多模态降级 / 与 ChatGPT 差异 / 商业化思考

### 📥 M6-04 · 部署
**估时**：4 h
**前置**：M5-09
**出口**：
- [ ] 后端 Dockerfile（含 PaddleOCR 模型预下载）
- [ ] 部署到 Render / Fly.io
- [ ] 前端 Vercel
- [ ] 公网 1 个可访问链接
- [ ] `docs/deployment.md` 写部署过程
- [ ] demo 期加 password gate（防刷 Claude 配额）

### 📥 M6-05 · README 美化 + 简历准备
**估时**：2 h
**前置**：M6-01, M6-02, M6-03
**出口**：
- [ ] README 顶部 badges + 架构图 + demo gif
- [ ] "为什么这个项目"段落
- [ ] 简历可加一行（公司名 + 链接 + 一句话）
- [ ] commit `M6: demo + deploy + interview ready`

---

## 横切任务（任意时候做）

### 📥 X-01 · 写 `scripts/new_skill.py`
**估时**：2 h
**前置**：M2-07
**出口**：
- [ ] 入参 `<subject> <question_type> --type=hybrid|llm|deterministic`
- [ ] 生成 skill .py + prompt 模板 + 测试 + fixture json 骨架
- [ ] 自动加注释 TODO 三处

### 📥 X-02 · 写 `scripts/start_full_stack.ps1`
**估时**：1 h
**前置**：M4-08
**出口**：
- [ ] 一键起：本地 LLM + uvicorn + Next.js dev
- [ ] 健康检查
- [ ] 失败时清晰报错

### 📥 X-03 · 调研 GPT-OSS 切换
**估时**：2 h
**前置**：GPT-OSS 发布后
**出口**：
- [ ] 选定模型版本（与 Gemma 4 同量级 / 更高）
- [ ] 跑通 llama-server 加载
- [ ] 更新 `EXAMSOLVER_LLM_MODEL_PATH` 与文档
- [ ] 路由 / 抽取任务质量回归 ≥ Gemma 4 水平

### 📥 X-04 · 监控 LLM 成本
**估时**：1 h
**前置**：M5-09
**出口**：
- [ ] `llm/claude_client.py` 落 tokens 使用到 SQLite `llm_usage` 表
- [ ] `GET /admin/usage` 日聚合
- [ ] 超过 $X/日时 log WARN

---

## 不在 backlog 的事（明确缓办）

- ❌ 用户 / 多租户
- ❌ 题目分享 / 社交
- ❌ 移动端
- ❌ 实时协作
- ❌ 全自动机构图重绘（v1.5 看精力）
- ❌ 非机械系学科批量扩展
- ❌ 视频 / 音频输入

---

## 进度追踪

每完成一张卡：
1. 改本文件状态 `📥 → ✅`
2. commit `<card-id>: <一句话描述>`
3. 检查后续卡的前置是否就绪

每周一次回顾：
- 哪些卡卡住了？为什么？
- 估时偏差大的卡，原因是什么？
- ROADMAP 里有需要同步调整的吗？

---

*文档状态：v1.0 初稿。新发现的任务直接加到对应 M 或 X，给个新编号。完成的卡保留在文件里（不删），方便回头看进度。*
