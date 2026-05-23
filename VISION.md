# Examsolver · 北极星 VISION v1.0（B 路线）

> **本文档定位**：当某个周末你怀疑这事儿值不值得做、当 Sonnet 4.6 接手时不知道方向，回来看这一份。它不是路线图，是**目的地的画像**。

---

## 0. 项目身份宣言

Examsolver 是：

1. **一个真实能用的产品** —— 大学生期末前 48 小时把一门陌生课"突击过线"的工具。
2. **一个可面试讲清楚的工程作品** —— LangGraph + 同心圆 skill 架构 + 多模态 + RAG 自编教材 + 笔记式前端，每一块都能拆开讲。

它不是：题库网站、搜题软件、GPT 套壳问答框、通用 chatbot、Wolfram Alpha。

**单一最重要承诺**：用户输入一道课内题（文本 / 图片 / 公式），输出**一页可保存可打印的笔记**，含步骤、答案、易错点、相关公式。不联网时图像理解会诚实说"做不了"，不假装。

---

## 1. 初心追溯（产品起点）

来自作者本人大学经历的**真实痛点**（不是想象的市场）：

| 课程 | 痛点 | 现有方案为什么不行 |
|---|---|---|
| 高数 | 题库"步骤略"，泰勒展开公式像英文 | 搜题软件给的是答案不是讲解；GPT 公式渲染烂、易跳步 |
| 公差与测量 | 老师自编教材，搜题搜不到 | 通用 AI 不知道这本教材的符号约定 |
| 机械原理 | 课本图糊，"几级齿轮传动""泄压阀在哪""曲柄连杆怎么动" | 纯文本模型看不懂图 |
| 大学物理 | 电子运动方向背不下来 | 缺图解、缺记忆卡 |
| 汽车理论 | 大题"某某起到什么作用"标准答案几百字 | 死记硬背没结构 |

**产品的合法性来自这些痛点**。每加一个 feature，问一句"它解决了上面哪条？"——没答案就不做。

---

## 2. 三类用户的 30 秒体验（v1.0 完成时）

### 用户 A：上课没听的大学生（核心用户）

```
[浏览器打开 localhost:3000]
[输入框]"用拉格朗日中值定理证明 sin x < x （x>0）"
[点解题]
→ 3 秒后右侧渲染出：
  · 题目（KaTeX 排版漂亮）
  · 解题思路（一句话点破"构造 f(x)=sin x - x，看导数符号"）
  · 步骤 1-4（公式逐行）
  · 最终答案
  · 易错点（"别忘了 cos x 在 (0, π/2) 严格小于 1"）
  · 相关公式速查（拉格朗日 / 柯西 / 罗尔，三选一卡片）
[点导出]→ word.docx 落到桌面，打印就能交
[加入错题本]→ 这道题进了"高数·中值定理"分组
```

### 用户 B：要看机械图的大学生（差异化用户）

```
[拍一张机械原理课本上糊的图]
[输入框]"这个机构是几级齿轮传动？传动比是多少？"
[上传图]
→ 后端先 PaddleOCR 抽出图上的标注文字（"齿数 z1=20, z2=40, z3=15, z4=60"）
→ 视觉理解走云端 Claude 4.6 多模态："这是两级齿轮传动，第一级 z1→z2，第二级 z3→z4"
→ skill `mechanism.gear_train` 算传动比：i = (z2/z1) × (z4/z3) = 2 × 4 = 8
→ 输出笔记：图重绘 + 步骤 + 传动比公式记忆卡
（无网时：返回 "OCR 提取的文字：...；视觉判断需联网，请联网后重试"）
```

### 用户 C：自编教材的受害者（杀手锏用户）

```
[在"我的资料"上传老师自编的《公差与测量》PDF]
→ 后端 PaddleOCR + chunk + embed，建索引（一次性，5 分钟）
[输入框]"基本偏差代号 H 和 h 有什么区别？"
→ RAG 检索教材中相关 chunks
→ LLM 基于教材语境回答（而不是通用知识）
→ 笔记里标注 "引自《公差与测量》第 3 章第 2 节"
```

---

## 3. 与对手的差异（面试时讲清楚）

| 对手 | 它的强 | 我们更强的地方 |
|---|---|---|
| 搜题软件（小猿、作业帮）| 题库覆盖广 | 自编教材搜不到 / 步骤略 / 没解释 |
| ChatGPT / Claude 网页版 | 通用强 | 公式渲染烂 / 没结构化笔记 / 无 RAG 课本 / 不能批量导出 |
| Wolfram Alpha | 计算精准 | 中文教材语境零 / 不讲解 / 没视觉 |
| Photomath | 拍照解 | 仅初等数学 / 没多学科 / 步骤模板化 |

**Examsolver 的位置**：中文大学生 × 机械系 × 突击场景。三条都满足时，对手都不强。

---

## 4. 三档目的地

| 里程碑 | 距今 | 一句话 | 验收 |
|---|---|---|---|
| **M3 可用版** | ~4 周 | 我自己能用它过一门期末考 | 真的用它复习并通过一门课的模拟卷 ≥ 70% |
| **M5 可演示版** | ~8 周 | 面试官 5 分钟看懂这是好项目 | demo 视频 < 3 分钟，4 个场景跑通无 bug |
| **M6 可投递版** | ~10 周 | 简历上写、能撑 30 分钟答辩 | 架构图 + 一页 STAR 描述 + GitHub 公开 + 部署链接 |

**这三档不是"功能更多"，是"演示更不丢人"**。

---

## 5. v1.0 完成时的样子

### 5.1 你打开仓库会看到

```
examsolver/
├── README.md / VISION.md / ARCHITECTURE.md / ROADMAP.md
├── SKILL_PLAYBOOK.md / FRONTEND.md / CONVENTIONS.md / BACKLOG.md
├── docs/
│   ├── demo.gif                          (3 分钟演示)
│   ├── architecture.png                  (LangGraph 节点图)
│   ├── interview-talk-track.md           (答辩话术 STAR 格式)
│   └── data-flow.md                      (一次解题的完整时序图)
├── src/examsolver/
│   ├── contracts/                        (旧契约 + 扩展 NoteEntry / Mistake)
│   ├── graph/                            (新：LangGraph 节点 + 边)
│   │   ├── nodes.py
│   │   ├── router_agent.py               (核心：决定走哪颗行星)
│   │   ├── state.py                      (SolveState TypedDict)
│   │   └── build.py
│   ├── skills/                           (同心圆：subject/<type>.py)
│   │   ├── _base/                        (Skill Protocol + 三型基类)
│   │   ├── general/                      (兜底：cot_with_textbook)
│   │   ├── calculus/                     (导数 / 积分 / 级数 / 微分方程)
│   │   ├── physics/                      (电磁 / 波动 / 刚体)
│   │   ├── mechanics_eng/                (力平衡 / 桁架 / 扭矩)
│   │   ├── mechanism/                    (曲柄连杆 / 齿轮 / 凸轮) [VLM]
│   │   ├── tolerance/                    (公差带 / 配合 / 形位) [RAG]
│   │   └── auto_theory/                  (动力性 / 制动性 / 操稳)
│   ├── multimodal/                       (新：OCR + VLM 客户端)
│   │   ├── ocr_paddle.py
│   │   ├── vlm_claude.py
│   │   └── fallback.py                   (无网降级)
│   ├── rag/                              (新：教材索引子系统)
│   │   ├── chunker.py
│   │   ├── embedder.py                   (sentence-transformers)
│   │   ├── store_sqlite_vec.py
│   │   └── retriever.py
│   ├── notes/                            (新：笔记 / 错题本)
│   │   ├── note_builder.py
│   │   ├── mistake_book.py
│   │   └── flashcard.py                  (突击卡片)
│   ├── export/                           (新：docx / pdf)
│   │   ├── docx_export.py
│   │   └── pdf_export.py                 (走前端 print)
│   ├── llm/                              (新：LLM client 抽象)
│   │   ├── base.py                       (Protocol)
│   │   ├── claude_client.py
│   │   ├── local_gguf.py                 (Gemma 4 / GPT-OSS)
│   │   └── router.py                     (依任务难度路由)
│   ├── api/                              (FastAPI 壳保留)
│   ├── pipeline/                         (旧 normalize/format 保留)
│   ├── services/                         (solve_service 改造为 graph 入口)
│   └── storage/                          (扩 notes / mistakes / documents / chunks 表)
├── frontend/                             (新：抢救 D:\codex file\ExamSolver)
│   ├── app/
│   │   ├── page.tsx                      (主工作台)
│   │   ├── note/[solve_id]/page.tsx      (一页一题视图)
│   │   ├── history/                      (历史)
│   │   ├── mistakes/                     (错题本)
│   │   ├── flashcards/                   (突击卡)
│   │   └── library/                      (我的教材)
│   ├── components/
│   ├── lib/
│   └── package.json
├── data/
│   ├── examsolver.db                     (SQLite + sqlite-vec)
│   ├── textbooks/                        (用户上传的 PDF)
│   └── exports/                          (生成的 docx)
└── scripts/
    ├── smoke.py
    ├── new_skill.py                      (脚手架)
    ├── index_textbook.py                 (PDF → embed → sqlite-vec)
    └── start_full_stack.ps1              (一键起后端+前端+本地 LLM)
```

### 5.2 数字快照（v1.0 验收）

| 指标 | 目标 |
|---|---|
| 真 skill 数 | ≥ 8 颗卫星（机械系 6 学科覆盖）|
| 文档化教材数 | ≥ 1 本（公差教材）|
| 笔记导出格式 | docx + pdf 双通道 |
| LangGraph 节点数 | ≥ 6（normalize / route / dispatch / enhance / format / persist）|
| 多模态可用 | OCR 本地 + VLM 云端 + 无网降级 3 条路全跑通 |
| 错题本 | 可标注 / 可分组 / 可导出 |
| 突击卡片 | 自动生成 ≥ 3 种（公式卡 / 易错卡 / 概念卡）|
| 演示视频 | < 3 分钟，4 个核心场景 |
| 部署 demo | ≥ 1 个公网可访问的链接 |

### 5.3 v1.0 当天的 vibe

你打开简历投出去，下面写着"AI 全栈项目：Examsolver"，链接点开就能用。面试官花 30 秒看 demo gif 就懂这是个**结构清晰、技术栈现代、有真实使用场景**的项目，而不是另一个 GPT 套壳 demo。

答辩时你能讲清：
- LangGraph 节点为什么这么分（**因为业务逻辑要在 skill 里，graph 只编排**）
- 同心圆架构怎么扩（**新加一颗卫星只需 4 步**，见 [`SKILL_PLAYBOOK.md`](./SKILL_PLAYBOOK.md)）
- 多模态怎么降级（**OCR 本地能跑，VLM 上云，无网时诚实说做不了**）
- RAG 为什么用 sqlite-vec（**零部署、与历史库同文件、单机够用**）

---

## 6. 与原"初心"的对照

| 初心要素 | v1.0 怎么实现 |
|---|---|
| 主体是通用解题思路，挂靠 skill | `skills/general/cot_with_textbook.py` 是兜底通用手 |
| Agent 负责分发 | `graph/router_agent.py` 用 LLM 判 subject + question_type，查 registry |
| 同心圆结构后端 | `skills/<subject>/<type>.py` 物理实现同心圆 |
| 太阳是 skill 元概念 | `skills/_base/protocol.py` 定 Skill Protocol（契约）|
| 行星是机械系学科 | `skills/calculus/` `mechanism/` `tolerance/` 等 |
| 卫星是题型 | 每个文件一颗卫星 |
| 留出恒星位置 | `skills/` 下任何 subject 文件夹都可加，registry 自动发现 |
| 一页一题 | 前端 `note/[solve_id]/page.tsx` 路由 |
| 可导出 Word PDF | `export/docx_export.py` + 浏览器 print |
| 公式渲染 | KaTeX |
| 图解能力 | VLM 输入 + 后端重绘机构图（v1.5 选做）|
| 突击记忆 | `notes/flashcard.py` 自动生成卡片 |
| 错题整理 | `notes/mistake_book.py` |
| 解题思路整理 | 笔记本身就是结构化思路 |

---

## 7. 明确不做的（护栏，到 v1.0 都不做）

- ❌ 用户系统 / 多租户 / 登录（单机本地优先）
- ❌ 题库 / 题目分享 / 社交
- ❌ 移动端原生 App（浏览器够用）
- ❌ 实时协作（一题一笔记，没必要）
- ❌ 训练自己的模型（用现成的）
- ❌ 商业化 / SaaS / 计费
- ❌ 开源运营（不维护 issue，不接 PR；公开但不运营）
- ❌ 非机械系学科扩展（除非高数 / 大学物理这种通用基础）
- ❌ 视频 / 音频输入
- ❌ 全自动机构图重绘（v1.5 再看）

---

## 8. 健康检查 · 一句话

**做完所有计划后，Examsolver 会是**：

> "一个我自己真的能拿来过期末、面试时能讲 30 分钟、技术上不丢人、产品上有真实用户痛点支撑的小作品。"

**它的最大成就不是 stars**——是**面试官看完会问"这个能商业化吗"**，是**学弟学妹真用它过了某门课**，是**一年后我自己回头看仍觉得架构干净**。

---

*文档状态：v1.0 初稿。B 路线首版。这是目的地的画像，预测会错，目的地不会。*
