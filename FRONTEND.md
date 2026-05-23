# 前端规约 v1.0

> Examsolver 前端的产品定位、技术选型、路由结构、设计系统、与后端 API 的契约。

---

## 0. 产品身份

**一句话**：一个**笔记本**，不是一个聊天框。

- 用户每解一道题，得到的是**一页可保存可打印的笔记**，不是一段对话回复
- 主路径不是输入框 + 历史消息流，而是输入框 → 跳转到 `/note/[id]` 笔记页
- 强可视化（公式、图、卡片），弱交互（不需要多轮对话）

---

## 1. 技术栈

| 维度 | 选型 |
|---|---|
| 框架 | Next.js 15 (App Router) |
| 视图 | React 19 |
| 语言 | TypeScript 5.9（strict）|
| 公式渲染 | KaTeX 0.16 |
| 状态 | RSC + `useState` 局部，**不引** zustand/redux |
| 样式 | CSS Modules + Design Token |
| 图标 | Lucide React |
| 字体 | Inter（已在旧仓库引入）|
| 包管理 | pnpm |

---

## 2. 旧仓库抢救清单

源：[`D:\codex file\ExamSolver`](D:/codex%20file/ExamSolver)

| 保留 | 不保留 |
|---|---|
| `app/` 路由骨架 | `lib/db.ts`（前端不直连 SQLite，走后端 API）|
| `components/` 视觉组件 | better-sqlite3 依赖 |
| `DESIGN.md`（Luminous Minimalist 设计系统）| docx 前端依赖（导出走后端）|
| `globals.css` 设计 token | 旧 `api/` route（后端走 FastAPI）|
| KaTeX 集成 |  |

迁移：复制 `app/` `components/` `lib/utils*` 到 `examsolver/frontend/`，删除 `app/api/` 与 SQLite 相关 lib。

---

## 3. 路由结构

```
frontend/app/
├── layout.tsx                       # 顶栏 + sidebar + 主区
├── page.tsx                         # / 主工作台
├── note/[solve_id]/page.tsx         # 一页一题
├── history/page.tsx                 # 历史列表
├── mistakes/
│   ├── page.tsx                     # 错题本总览（按 subject 分组）
│   └── [subject]/page.tsx           # 单学科错题列表
├── flashcards/
│   ├── page.tsx                     # 卡片库（按 note_id 分组）
│   └── session/[solve_id]/page.tsx  # 抽认卡 session
├── library/page.tsx                 # 教材管理（上传、索引、列表）
└── about/page.tsx                   # 关于（vision 摘要）
```

### 3.1 sidebar

固定左侧 240px：
- 工作台（/）
- 历史（/history）
- 错题本（/mistakes）
- 卡片（/flashcards）
- 教材（/library）
- 分割线
- 最近 10 条笔记（小字、可点）

### 3.2 顶栏

简洁。左侧 logo + 项目名，右侧 LLM 状态指示器（云 / 本地 / 离线）+ 设置入口（v1.1 再做）。

---

## 4. 主工作台 `/` 设计

**单一焦点**：解题入口。

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│                                                         │
│            Examsolver · 大学生突击复习助手               │
│                                                         │
│         一道题，一页笔记。                               │
│                                                         │
│   ┌─────────────────────────────────────────────────┐   │
│   │  把题贴这里。可附图。                            │   │
│   │                                                 │   │
│   │                                                 │   │
│   └─────────────────────────────────────────────────┘   │
│   [📎 附图]  [▼ 学科：自动判断]          [→ 解题]      │
│                                                         │
│   建议从这些题开始 →                                    │
│   [求导] [配合判断] [齿轮传动比] [动力性]               │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**交互**：
- 提交后 → `POST /solve` → 拿到 `solve_id` → `router.push(\`/note/${solve_id}\`)`
- 中途显示骨架屏 + "正在路由 → 求解 → 生成笔记..." 进度文案
- 附图：拖拽 / 点选，缩略图预览

---

## 5. 一页一题 `/note/[solve_id]`

**核心视图**。这是产品身份的兑现。

### 5.1 结构

```
┌───────────────────────────────────────────────────────────────┐
│ [← 返回] [机械原理]                  [+错题] [📄 docx] [🖨]   │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  齿轮传动比计算                                                │
│  ─────────────                                                │
│                                                               │
│  题目                                                          │
│  两级齿轮传动，z₁=20, z₂=40, z₃=15, z₄=60，传动比？          │
│                                                               │
│  💡 思路                                                       │
│  传动比逐级相乘：i = i₁ × i₂ = (z₂/z₁) × (z₄/z₃)              │
│                                                               │
│  步骤                                                          │
│  1. 第 1 级：i₁ = z₂/z₁ = 40/20 = 2                          │
│  2. 第 2 级：i₂ = z₄/z₃ = 60/15 = 4                          │
│  3. 总传动比：i = i₁ × i₂ = 8                                │
│                                                               │
│  答案                                                          │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│   总传动比 i = 8                                              │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                               │
│  ⚠ 易错点                                                      │
│  · 别把"驱动"和"被驱动"齿数搞反                                │
│  · 多级传动是相乘不是相加                                       │
│                                                               │
└───────────────────────────────────────────────────────────────┘

侧栏（右 320px，sticky）：

  📐 公式速查
  ┌──────────────────────────┐
  │ 单级齿轮传动比            │
  │ i = z₂ / z₁              │
  │ z 是齿数                  │
  └──────────────────────────┘

  ┌──────────────────────────┐
  │ 多级齿轮传动              │
  │ i_total = ∏ i_k          │
  └──────────────────────────┘

  🎴 已生成卡片 (3)
  · 公式卡：齿轮传动比
  · 概念卡：何为多级传动
  · 易错卡：齿数主从

  📚 引用（如有）
  · 《机械原理》P32

```

### 5.2 字段对应

后端 `NoteEntry` 字段直接渲染：

| NoteEntry 字段 | 视图位置 |
|---|---|
| `title` | 顶部 h1 |
| `subject` | 顶部 chip |
| `question_latex` | 题目区，KaTeX 渲染 |
| `student_explanation.thinking` | 💡 思路 |
| `steps[].description` | 步骤列表项主文本 |
| `steps[].formula_latex` | 步骤列表项下方 KaTeX |
| `steps[].image_hint` | 如有，对应图区 |
| `answer` | 答案块（醒目）|
| `common_mistakes` | ⚠ 易错点 |
| `related_formulas` | 右侧公式速查 |
| `flashcards` | 右侧卡片入口 |
| `citations` | 右侧引用 |

### 5.3 顶部工具栏动作

| 按钮 | 行为 |
|---|---|
| ← 返回 | `router.back()` |
| 学科 chip | 点击 → 跳转 `/history?subject=<x>` |
| ➕ 错题 | `POST /mistakes` |
| 📄 docx | 下载 `/export/docx/{solve_id}` |
| 🖨 打印 | `window.print()`（走 print CSS）|

### 5.4 KaTeX 集成

- 安装：`pnpm add katex react-katex`（或直接 `@matejmazur/react-katex`）
- 渲染：`<BlockMath math={step.formula_latex} />`
- 多次渲染 = 性能问题：用 `<MemoizedFormula>` 包裹

---

## 6. 历史 `/history`

按时间倒序列表。每条卡片：

```
┌─────────────────────────────────────────────────┐
│ [机械原理]  齿轮传动比计算          2026-05-17  │
│ z₁=20, z₂=40, z₃=15, z₄=60                     │
│ 答案：i = 8                                     │
└─────────────────────────────────────────────────┘
```

- 顶部筛选：学科 chips + 日期范围
- 点击卡片 → `/note/[solve_id]`
- 支持搜索框（关键词匹配 question 与 answer）

---

## 7. 错题本 `/mistakes`

### 7.1 主页（按学科分组）

```
高数（12 题）  ▶
机械原理（5 题）▶
公差与测量（3 题）▶
```

### 7.2 子页 `/mistakes/[subject]`

按 question_type 分组的笔记列表，每条可：
- 点开看完整笔记（跳 `/note/[solve_id]`）
- 加批注（弹窗，直接 PATCH 后端）
- 移除（DELETE 后端）

### 7.3 批量导出

顶部按钮 "导出全部 docx"：
- `POST /export/docx/batch` body `{solve_ids: [...]}`
- 返回 zip 流

---

## 8. 卡片 `/flashcards`

### 8.1 卡片库

按 note 分组，每个 note 下挂 N 张卡。可勾选若干 → "开始 session"。

### 8.2 Session `/flashcards/session/[solve_id]`

抽认卡 UI：

```
┌─────────────────────────────────────────┐
│                                         │
│              问题面                      │
│                                         │
│        齿轮传动比公式 i = ?              │
│                                         │
│                                         │
│         [空格 翻面]                      │
└─────────────────────────────────────────┘
```

按空格 → 翻面显示答案。
左 / 右 / 上 / 下 箭头：上一张 / 下一张 / 标会 / 标不会。

session 结束后展示统计（共 N 张，会 X 张，不会 Y 张）。

---

## 9. 教材 `/library`

### 9.1 列表

每行：标题 + 学科 + 页数 + chunks 数 + 操作（重新索引 / 删除）。

### 9.2 上传

```
┌─────────────────────────────────────────┐
│ + 上传新教材                            │
│                                         │
│ 拖拽 PDF 到此                           │
│ 学科：[下拉选 / 自动判断]               │
│ 标题：[输入]                            │
│                                         │
│         [开始索引]                      │
└─────────────────────────────────────────┘
```

- `POST /library/upload` 返回 document_id
- 自动触发 `POST /library/index/{document_id}`
- 实时显示进度（SSE 或轮询）

---

## 10. 设计系统（Luminous Minimalist）

完全沿用 [`D:\codex file\ExamSolver\DESIGN.md`](D:/codex%20file/ExamSolver/DESIGN.md)。要点：

### 10.1 颜色
| Token | Hex | 用途 |
|---|---|---|
| `surface` | `#f9f9fb` | 主背景 |
| `surface-container-low` | `#f3f3f5` | 大结构（sidebar）|
| `surface-container-lowest` | `#ffffff` | 主卡片 |
| `primary` | `#0058bc` | 主操作按钮 |
| `primary-container` | `#0070eb` | 主操作渐变末端 |
| `on-surface` | `#1a1c1d` | 主文字（**不用纯黑**）|

### 10.2 无线条规则
**禁止 1px 实线**作为分割。用：
- 背景色差
- 4px 色块
- 24px 空白

### 10.3 玻璃态
浮层（modal / tooltip）：
- 70% 不透明度的 `surface-container-lowest`
- backdrop-blur 24px
- 0px 12px 32px rgba(26, 28, 29, 0.06) 阴影

### 10.4 按钮
- Primary：胶囊形（9999px radius），渐变 `primary → primary-container`
- Secondary：`surface-container-highest` 背景，无边框
- Tertiary：透明背景，`primary` 文字

### 10.5 圆角
- 卡片：1.5rem（24px）
- 输入框：0.75rem（12px）
- 标签 chip：0.5rem（8px）

### 10.6 排版
- Display：3.5rem，letter-spacing -0.02em，bold
- Headline：1.75rem
- Body：1rem
- Label / metadata：0.75rem，全大写

---

## 11. 与后端 API 的契约

### 11.1 端点清单

| Method | Path | 用途 |
|---|---|---|
| POST | `/solve` | 提交题目 |
| GET | `/solve/{solve_id}` | 取笔记 |
| GET | `/solve/history?subject=&limit=` | 历史 |
| POST | `/mistakes` | 加入错题本 |
| GET | `/mistakes?subject=` | 错题列表 |
| DELETE | `/mistakes/{id}` | 移除 |
| PATCH | `/mistakes/{id}` | 改批注 |
| GET | `/export/docx/{solve_id}` | 导出单题 docx |
| POST | `/export/docx/batch` | 批量 docx zip |
| GET | `/library` | 教材列表 |
| POST | `/library/upload` | 上传教材 |
| POST | `/library/index/{doc_id}` | 索引 |
| DELETE | `/library/{doc_id}` | 删教材 |
| GET | `/llm/status` | LLM 健康检查 |

### 11.2 SolveResponse 形状

详见 [`ARCHITECTURE.md §4.5`](./ARCHITECTURE.md)。前端 type：

```typescript
// frontend/lib/types.ts
export type Step = {
  index: number;
  description: string;
  formula_latex: string | null;
  image_hint: string | null;
};

export type Citation = {
  source: string;
  chunk_id: string;
  page: number | null;
  snippet: string;
};

export type Flashcard = {
  front: string;
  back: string;
  card_type: "formula" | "concept" | "trap";
};

export type NoteEntry = {
  solve_id: string;
  title: string;
  question_latex: string;
  steps: Step[];
  answer: string | Record<string, unknown>;
  student_explanation: { thinking: string; tone: string } | null;
  common_mistakes: string[];
  related_formulas: { title: string; latex: string }[];
  flashcards: Flashcard[];
  citations: Citation[];
  subject: string;
  question_type: string;
  created_at: string;
};

export type SolveResponse = {
  success: boolean;
  solve_id: string;
  subject: string;
  question_type: string;
  note: NoteEntry;
  message: string;
  fallback_reasons: string[];
};
```

### 11.3 错误处理

- 任何 5xx → toast "服务异常，请稍后重试"
- `success=false` → 在笔记区域上方红条显示 `message`
- `fallback_reasons` 含 `"vlm_offline"` → 笔记上方黄条"图像理解需联网"

---

## 12. 性能

| 指标 | 目标 |
|---|---|
| 首屏 LCP | < 1.5s |
| 笔记页渲染 | KaTeX < 200ms（用 memoize）|
| 路由切换 | 视觉 < 100ms（用骨架屏）|
| 上传 PDF | < 5MB 无感，> 5MB 显示进度 |

---

## 13. 打印 / 导出策略

### 13.1 浏览器打印 → PDF
- print stylesheet：隐藏 sidebar / 顶栏 / 工具栏，**一页一题强制 page-break**
- 公式仍以 KaTeX SVG/HTML 渲染（清晰）

### 13.2 后端 docx
- 走 `/export/docx/{solve_id}`，下载触发
- 文件名格式 `{subject}-{title}-{date}.docx`

---

## 14. 红线

- ❌ 前端直连数据库（必须经后端 API）
- ❌ 在前端调 LLM（成本不可控）
- ❌ 用 1px 边框分割
- ❌ 用纯黑 `#000` 文字
- ❌ 引入 redux / zustand 大状态库
- ❌ 公式在 docx 里以图片形式输出（OMML 优先）
- ❌ 笔记页超过两层弹窗（保持极简）
- ❌ 移动端响应式（v1.0 桌面优先，不为移动端妥协设计）

---

## 15. 启动

```bash
# 一次性
cd frontend
pnpm install

# 日常
pnpm dev      # localhost:3000
```

需要后端先起：

```bash
uv run uvicorn examsolver.api.app:app --reload
```

或者一键：

```powershell
.\scripts\start_full_stack.ps1
```

---

*文档状态：v1.0 初稿。前端调整时同步本文件。*
