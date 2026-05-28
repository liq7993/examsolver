# Examsolver 代码与工程约定 v1.0（B 路线）

> 代码层规约。冲突时以 [`ARCHITECTURE.md`](./ARCHITECTURE.md) 为准。

---

## 1. 语言与运行环境

- **Python 3.11+**（typing.Self、tomllib、sqlite-vec 需要新版 sqlite）
- **TypeScript 5.9+ / Next.js 15 / React 19**（前端）
- **标准库优先**：`logging` / `sqlite3` / `dataclasses` / `uuid` / `json` / `pathlib`
- **运行时核心依赖**（写进 `pyproject.toml` `[project] dependencies`）：
  ```
  fastapi
  uvicorn
  pydantic>=2
  langgraph
  anthropic
  openai                            # OpenAI 兼容 client，连本地 llama-server
  paddleocr                         # 备选 rapidocr-onnxruntime
  paddlepaddle
  sentence-transformers
  sqlite-vec
  python-docx
  pypdf
  pillow
  httpx
  ```
- **dev 依赖**：`pytest` `pytest-cov` `ruff` `mypy` `respx`（mock httpx）

---

## 2. 项目元数据

- `pyproject.toml` 用 hatchling / uv backend
- `src/` layout，包路径 `src/examsolver/`
- 前端独立 `frontend/`，自己的 `package.json`

---

## 3. 代码风格与静态检查

- **ruff**：formatter + linter，line-length 100
- **mypy strict**（`[[tool.mypy.overrides]]` 可对 paddleocr 等无类型库放宽）
- 所有公开函数 / 方法必须有类型注解
- 契约（`contracts/`）一律 `@dataclass(frozen=True, slots=True)`
- HTTP schema（`api/schemas.py`）用 `pydantic.BaseModel`
- 模块首行 docstring 说明本模块在架构里的位置
- 禁止 `from x import *`、禁止裸 `except:`

---

## 4. 日志约定

### 4.1 使用 stdlib `logging`
- `logging.getLogger(__name__)`，入口处一次 `basicConfig`
- **不用** `print`，不用第三方结构化日志框架

### 4.2 级别
| 级别 | 场景 |
|---|---|
| `DEBUG` | 本地调试；生产关 |
| `INFO` | 请求生命周期、节点入口出口、LLM 调用、外部 API 调用 |
| `WARNING` | 可恢复降级（VLM 离线、RAG 无命中、持久化失败）|
| `ERROR` | 不可恢复（契约破坏、未捕获异常）|

### 4.3 格式
```
[<request_id>] <LEVEL> <module.function>: <message>
```

示例：
```
[8fa3c1b2] INFO  graph.nodes.normalize_node: begin
[8fa3c1b2] INFO  graph.router_agent: subject=mechanism type=gear_train conf=0.92 reason=...
[8fa3c1b2] INFO  llm.claude_client.chat: tokens_in=412 tokens_out=287 latency=1.34s
[8fa3c1b2] WARN  multimodal.fallback: vlm offline; skipping vision
[8fa3c1b2] INFO  services.solve_service: done success=true
```

### 4.4 禁止
- 一次请求 > 15 条 INFO（避免刷屏）
- log 里出现 API key / 用户原文密码
- stack trace 拼到 `SolveResponse.message`（走 diagnostics）
- 长 prompt 全文记 log（仅记 task_kind + tokens 数）

---

## 5. 消息语言策略

- `NoteEntry.*` / `SolveResponse.message` / `student_explanation` / `common_mistakes` —— **中文**
- log / 异常 message / 代码注释 —— 中英皆可，简洁优先
- LLM prompt —— **prompt 模板放独立文件** `<skill>/prompts/<name>.zh.md`
- **不做 i18n**

---

## 6. 命名约定

| 对象 | 命名 | 示例 |
|---|---|---|
| 模块文件 | `snake_case` | `gear_train.py` |
| 类 | `PascalCase` | `GearTrainSkill` |
| 函数 / 方法 | `snake_case` | `classify_question` |
| 常量 | `SCREAMING_SNAKE_CASE` | `MAX_OCR_PAGES` |
| 私有 | `_leading_underscore` | `_round_to_3` |
| `skill.name` | `<subject>.<question_type>` | `"mechanism.gear_train"` |
| `skill.version` | SemVer | `"0.1.0"` |
| `subject` | `snake_case` | `"calculus"` `"mechanism"` |
| `question_type` | `snake_case` | `"derivative"` `"gear_train"` |
| LangGraph 节点 | `<verb>_node` | `normalize_node` `ocr_node` |
| LLM task_kind | `snake_case` | `"route"` `"extract_simple"` `"synthesize"` |

**避免缩写**：`question` 不写 `q`，`request` 不写 `req`（局部变量可宽松）。

---

## 7. Skill 版本规则（SemVer）

| 级别 | 触发 |
|---|---|
| PATCH `0.1.0 → 0.1.1` | bugfix、prompt 微调、不影响 `answer` 含义 |
| MINOR `0.1.1 → 0.2.0` | 新增子题型、增强 steps、向后兼容 |
| MAJOR `0.2.0 → 1.0.0` | answer 语义变 / steps 结构断裂 / Skill Protocol 不兼容 |

- 历史 `result_json` 必须落 `skill_version`
- 回放历史时按版本判断兼容性

---

## 8. `hints` / `meta` / `state` 命名空间

### 8.1 `NormalizedQuestion.hints`（共享区）
- 通用前缀无：`hints["request_id"]` `hints["has_latex"]`
- skill 专属：`hints["<subject>.<key>"]`，例 `hints["mechanism.gear_count"]=4`

### 8.2 `SolveResult.meta`
- skill 输出的扩展必带 `<subject>.<type>.<key>` 前缀：
  ```
  meta["mechanism.gear_train.ratio"] = 8.0
  meta["mechanism.gear_train.stages"] = 2
  ```

### 8.3 `SolveState`（LangGraph）
- 字段名扁平，由 [`graph/state.py`](src/examsolver/graph/state.py) 统一定义
- 节点只写自己负责的字段，禁止覆盖别人的字段
- 节点之间通信走 state，**不**走全局变量

### 8.4 保留键（框架专属）
以下键只能由框架写：
- `hints["request_id"]` `hints["solve_id"]` `hints["created_at"]`
- `meta["skill_version"]`
- `state.errors` `state.fallback_reasons`（节点 append，禁止 reassign）

---

## 9. 测试约定

### 9.1 组织
- `tests/` 镜像 `src/examsolver/`
- 文件命名 `test_<obj>.py`
- 夹具集中 `tests/fixtures/`

### 9.2 隔离
| 层 | 禁止 |
|---|---|
| `tests/contracts/` | import 任何业务模块 |
| `tests/skills/` | import FastAPI / sqlite3；调真 LLM（用 FakeLLM）|
| `tests/graph/` | 启 HTTP server；调真 LLM |
| `tests/multimodal/` | 调真 Claude API（用 mock）|
| `tests/rag/` | 写真磁盘外的目录（用 tmp_path）|
| `tests/api/` | 连真 DB（用 in-memory sqlite）|

### 9.3 FakeLLM
- `tests/_helpers/fake_llm.py` 提供 `FakeLLMClient` 实现 `LLMClient` Protocol
- 行为：根据 task_kind + prompt hash 返回预录响应
- 任何 LLM-related 测试必须用它

### 9.4 回归夹具
- skill 必有 `tests/skills/<subject>/<type>_regression.json`
- 至少 3 条样本
- 用 `pytest.mark.parametrize` 批量断言关键字段

### 9.5 覆盖率
- 不强求 100%
- 契约 / pipeline / 关键 skill happy path 必有
- 异常路径 / unknown 路径优先级高于内部纯函数

---

## 10. Git / 工作区卫生

### 10.1 `.gitignore` 必含
```
.venv/
__pycache__/
*.egg-info/
dist/
build/
.pytest_cache/
.mypy_cache/
.ruff_cache/
*.db
*.db-journal
data/textbooks/
data/exports/
.env
.env.local
node_modules/
frontend/.next/
frontend/out/
_archive_old_oss_plan/         # 归档不需要进新 git
```

### 10.2 Commit message
- 建议：`<layer>: <change>`
- 例：`graph: add router_agent_node`、`skills: tolerance.fit_type initial`

### 10.3 分支
- 单人推 main
- 实验性分支前缀 `wip/`

---

## 11. 命令清单

| 命令 | 作用 |
|---|---|
| `uv sync` | 装依赖 |
| `uv run pytest` | 跑测试 |
| `uv run pytest -k <kw>` | 跑特定测试 |
| `python scripts/smoke.py "<题>"` | 不经 HTTP 跑一道题 |
| `uv run uvicorn examsolver.api.app:app --reload` | 启 HTTP |
| `pnpm dev`（在 frontend/）| 启前端 |
| `uv run ruff check . && uv run ruff format .` | lint + format |
| `uv run mypy src` | 类型检查 |
| `python scripts/new_skill.py <subject> <type>` | 新 skill 脚手架 |
| `python scripts/index_textbook.py <pdf> --subject <s>` | 索引教材 |
| `.\scripts\start_full_stack.ps1` | 一键起后端 + 前端 + 本地 LLM |

---

## 12. LangGraph 节点写法约定

### 12.1 形状
```python
def my_node(state: SolveState) -> SolveState:
    """职责一句话。"""
    request_id = state["request_id"]
    logger.info("[%s] my_node: begin", request_id)
    try:
        # 业务
        result = _do_work(state)
        state["my_output"] = result
    except RecoverableError as exc:
        state["fallback_reasons"].append(f"my_node:{exc}")
        logger.warning("[%s] my_node: fallback %s", request_id, exc)
    logger.info("[%s] my_node: done", request_id)
    return state
```

### 12.2 红线
- 节点函数**不带副作用**（除 state 修改和 log）
- 节点函数**不抛**未捕获异常（除非是契约违反）
- 节点**不调** skill 之间相互引用
- 节点**不依赖全局**单例（client 通过 state 或参数注入）

### 12.3 节点必须做的
- 入口 INFO log
- 出口 INFO log
- 异常时 append `state.fallback_reasons`
- 修改的字段在 [`graph/state.py`](src/examsolver/graph/state.py) 有声明

---

## 13. LLM 调用约定

### 13.1 必须走抽象层
- 所有 LLM 调用通过 `LLMClient` Protocol
- 禁止在 skill / node 里直接 `import anthropic` / `import openai`
- 选 client 走 `llm.router.pick_llm(task_kind, needs_vision)`

### 13.2 Prompt 文件
- 模板放 `src/examsolver/skills/<subject>/prompts/<name>.zh.md`
- 加载用 `pathlib.Path(__file__).parent / "prompts" / "..."`
- 大段 prompt 不内联在代码字符串里

### 13.3 JSON 结构化输出
- 任何需要解析 LLM 输出的地方必须用 JSON schema
- 解析失败 → 重试 1 次 → 仍失败走 fallback
- schema 放在 skill 同文件，命名 `<name>_SCHEMA`

### 13.4 成本与超时
- `max_tokens` 默认 1024，必要时显式抬
- 超时默认 30s（云）/ 60s（本地）
- task_kind="route" 强制本地优先（便宜）

---

## 14. 多模态约定

### 14.1 图像路径
- 输入是 `list[str]`（路径），不是 bytes
- 路径必须在 `data/uploads/` 或临时目录下
- 节点内部读 bytes 再传给 client

### 14.2 OCR
- 单例引擎（lazy 加载）
- 失败抛 `OCRError`，graph 标记继续
- 输出 bbox 用 `dict` 而非 numpy array（state 可序列化）

### 14.3 VLM
- 仅 Claude，写死
- 离线判定：调用前 `multimodal/fallback.check_cloud_reachable()`
- 离线时 `vlm_node` 跳过，写 `state.fallback_reasons.append("vlm_offline")`

---

## 15. RAG 约定

### 15.1 chunk 规格
- 长度 500 字（中文按字符计）
- 重叠 100 字
- 不跨章节强行合并（按 PDF heading 切）

### 15.2 embedding
- 模型固定 `paraphrase-multilingual-MiniLM-L12-v2`（384 维）
- 首次使用 sentence-transformers 可能下载约 500MB 模型文件
- 可用 `EXAMSOLVER_EMBED_MODEL` 指向本地模型路径或兼容模型名
- 切换模型 → 必须重建索引 → 文档警告

### 15.3 检索
- 默认 top_k=5
- 距离阈值 cosine_distance < 0.5 才算命中
- 不命中返回空 list，不抛异常

---

## 16. 前端约定（详见 [`FRONTEND.md`](./FRONTEND.md)）

- TypeScript 严格模式
- 设计系统：Luminous Minimalist（沿用旧 DESIGN.md）
- 状态：React Server Components + useState 局部
- 不引大状态库（zustand 等）
- 公式渲染：KaTeX
- 颜色 / 间距 / 字体 走 design token

---

## 17. 红线速查（写代码前扫一眼）

- ❌ `skills/` 下 import `langgraph` / `fastapi` / `sqlite3`
- ❌ `graph/nodes.py` 里写业务解题逻辑
- ❌ 一个 skill import 另一个 skill（用 `_utils/`）
- ❌ Pydantic 模型当 contract（contract 用 dataclass）
- ❌ 任何层抛 `HTTPException`（FastAPI 路由层捕获后转）
- ❌ `request_id` 进 response body（进 diagnostics）
- ❌ 契约字段删除 / 语义变（必须升主版本）
- ❌ skill 直接 `import anthropic` / `import openai`
- ❌ 路由文件 > 50 行
- ❌ `print()` 出现在任何 .py
- ❌ 长 prompt 全文落 log
- ❌ 把图片原始 bytes 塞进 LangGraph state（用路径）
- ❌ commit 前不跑 `pytest`
- ❌ 在 `_archive_old_oss_plan/` 里改东西（已废弃，仅参考用）

---

*文档状态：v1.0 初稿。约定层改动门槛比架构低；发现更好的做法可以直接修订本文件，但需 commit message 说明"为什么改"。*
