const state = {
  pages: [],
  currentIndex: -1,
  activeStepIndex: 0,
  busy: false,
};

const els = {
  form: document.querySelector("#solve-form"),
  input: document.querySelector("#question-input"),
  submit: document.querySelector("#submit-button"),
  empty: document.querySelector("#empty-page"),
  noteStack: document.querySelector("#note-stack"),
  pagePrev: document.querySelector("#page-prev"),
  pageNext: document.querySelector("#page-next"),
  pageIndicator: document.querySelector("#page-indicator"),
  problemSubject: document.querySelector("#problem-subject"),
  problemType: document.querySelector("#problem-type"),
  problemTime: document.querySelector("#problem-time"),
  problemText: document.querySelector("#problem-text"),
  resultStatus: document.querySelector("#result-status"),
  statusKind: document.querySelector("#status-kind"),
  statusMessage: document.querySelector("#status-message"),
  pageTools: document.querySelector("#page-tools"),
  copyAnswer: document.querySelector("#copy-answer"),
  copyNote: document.querySelector("#copy-note"),
  downloadNote: document.querySelector("#download-note"),
  exportPdf: document.querySelector("#export-pdf"),
  toolFeedback: document.querySelector("#tool-feedback"),
  answerSkill: document.querySelector("#answer-skill"),
  answerText: document.querySelector("#answer-text"),
  stepsMeta: document.querySelector("#steps-meta"),
  stepsLayout: document.querySelector("#steps-layout"),
  formulasPanel: document.querySelector("#formulas-panel"),
  formulasMeta: document.querySelector("#formulas-meta"),
  formulaList: document.querySelector("#formula-list"),
  explanationPanel: document.querySelector("#explanation-panel"),
  explanationGrid: document.querySelector("#explanation-grid"),
  history: document.querySelector("#history-list"),
  newThread: document.querySelector("#new-thread"),
};

const labels = {
  subject: {
    mechanics: "工程力学",
    calculus: "微积分",
    linear_algebra: "线性代数",
    mechanism: "机械原理",
    tolerance: "公差配合",
    general: "通用",
    unknown: "未识别",
  },
  type: {
    force_balance: "受力平衡",
    derivative: "求导",
    matrix_mul: "矩阵乘法",
    gear_train: "齿轮传动",
    fit_type: "配合类型",
    general: "通用解答",
    unknown: "未识别",
  },
};

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function localize(map, value) {
  return map[value] || value || "未识别";
}

function formatAnswer(answer) {
  if (answer === null || answer === undefined || answer === "") return "无答案";
  if (typeof answer === "string") return answer;
  if (typeof answer === "object") {
    return Object.entries(answer)
      .map(([key, value]) => `${key}: ${value}`)
      .join(" · ");
  }
  return String(answer);
}

function markdownValue(value) {
  if (value === null || value === undefined || value === "") return "无答案";
  if (typeof value === "string") return value;
  return Object.entries(value)
    .map(([key, item]) => `- ${key}: ${item}`)
    .join("\n");
}

function collectText(value) {
  if (value === null || value === undefined) return [];
  if (typeof value === "string") return [value];
  if (Array.isArray(value)) return value.flatMap(collectText);
  if (typeof value === "object") return Object.values(value).flatMap(collectText);
  return [String(value)];
}

function extractLatexSegments(...values) {
  const seen = new Set();
  const formulas = [];
  const pattern = /\${1,2}([^$]+?)\${1,2}/g;
  collectText(values).forEach((text) => {
    for (const match of String(text).matchAll(pattern)) {
      const latex = match[1].trim();
      if (!latex || seen.has(latex)) continue;
      seen.add(latex);
      formulas.push(latex);
    }
  });
  return formulas;
}

function renderLatexLite(source) {
  let html = escapeHtml(source.trim());
  html = html.replace(
    /\\frac\{([^{}]+)\}\{([^{}]+)\}/g,
    '<span class="formula-frac"><span>$1</span><span>$2</span></span>',
  );
  html = html
    .replaceAll("\\times", "×")
    .replaceAll("\\cdot", "·")
    .replaceAll("\\sum", "∑")
    .replaceAll("\\theta", "θ")
    .replaceAll("\\Delta", "Δ")
    .replaceAll("\\mathrm", "")
    .replaceAll("\\begin{bmatrix}", "[")
    .replaceAll("\\end{bmatrix}", "]")
    .replaceAll("\\\\", " ; ")
    .replace(/\{([^{}]+)\}/g, "$1")
    .replace(/\^circ/g, "°")
    .replace(/\^([A-Za-z0-9+-]+)/g, "<sup>$1</sup>")
    .replace(/_([A-Za-z0-9+-]+)/g, "<sub>$1</sub>");
  return `<span class="formula-rendered">${html}</span>`;
}

function normalizeMathSource(value) {
  return String(value || "")
    .replace(/\\f\s*rac/g, "\\frac")
    .replace(/�\s*rac/g, "\\frac")
    .replace(/\\t\s*ext\s*\{\s*([^}]+?)\s*\}/g, "\\text{$1}")
    .replace(/\t\s*ext\s*\{\s*([^}]+?)\s*\}/g, "\\text{$1}")
    .replace(/\\t\s*ext\s+([A-Za-z]+)/g, "\\text{$1}")
    .replace(/\t\s*ext\s+([A-Za-z]+)/g, "\\text{$1}")
    .replace(/\bext\s*\{\s*([^}]+?)\s*\}/g, "\\text{$1}")
    .replace(/\bext\s*(N|kN|m|s|kg)\b/g, "\\text{$1}")
    .replace(/\\CIRC\b/g, "\\circ")
    .replace(/\\c(?:irc)?\$/gi, "\\circ")
    .replace(/\bCIRC\b/g, "\\circ");
}

function renderLatex(source, displayMode = true) {
  const normalized = normalizeMathSource(source);
  const fallback = renderLatexLite(normalized);
  if (window.katex && typeof window.katex.renderToString === "function") {
    try {
      return window.katex.renderToString(normalized.trim() || "\\ ", {
        displayMode,
        output: "html",
        throwOnError: false,
      });
    } catch (error) {
      return `<span class="formula-error">公式渲染失败：${escapeHtml(error.message || "unknown")}</span>${fallback}`;
    }
  }
  return fallback;
}

function renderMathText(value) {
  const text = String(value || "");
  const pattern = /(\$\$[\s\S]+?\$\$|\$[^$\n]+?\$)/g;
  let html = "";
  let cursor = 0;

  for (const match of text.matchAll(pattern)) {
    const raw = match[0];
    const index = match.index || 0;
    const displayMode = raw.startsWith("$$");
    const delimiterLength = displayMode ? 2 : 1;
    const source = raw.slice(delimiterLength, -delimiterLength).trim();

    html += escapeHtml(text.slice(cursor, index));
    html += renderLatex(source, displayMode);
    cursor = index + raw.length;
  }

  html += escapeHtml(text.slice(cursor));
  return html;
}

function formatTime(value) {
  if (!value) return new Date().toLocaleString("zh-CN", { hour: "2-digit", minute: "2-digit" });
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("zh-CN", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function shortStep(text, max = 36) {
  const clean = String(text).replaceAll("$", "").replaceAll("\\", "");
  const first = clean.split(/[。！？.!?\n]/)[0] || clean;
  return first.length > max ? `${first.slice(0, max)}…` : first;
}

function setBusy(nextBusy) {
  state.busy = nextBusy;
  els.submit.disabled = nextBusy;
  els.submit.textContent = nextBusy ? "…" : "↑";
}

function setStatus(kind, message) {
  els.resultStatus.hidden = false;
  els.resultStatus.setAttribute("data-status", kind);
  els.statusKind.textContent = kind;
  els.statusMessage.textContent = message || "等待解题结果";
}

async function copyText(value) {
  const text = String(value || "");
  if (!text) return false;

  if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
    await navigator.clipboard.writeText(text);
    return true;
  }

  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.append(textarea);
  textarea.select();
  const copied = document.execCommand("copy");
  textarea.remove();
  return copied;
}

function showToolFeedback(message) {
  els.toolFeedback.textContent = message;
  window.setTimeout(() => {
    els.toolFeedback.textContent = "";
  }, 1800);
}

function noteMarkdown(page) {
  const solve = page.solve;
  const explanation = solve.student_explanation;
  const lines = [
    `# ${localize(labels.subject, solve.subject)} · ${localize(labels.type, solve.question_type)}`,
    "",
    `- Solve ID: ${solve.solve_id}`,
    `- Skill: ${solve.skill || "unknown"}`,
    `- Time: ${formatTime(page.createdAt)}`,
    `- Status: ${solve.success ? "success" : "unsupported"}`,
    "",
    "## 题目",
    "",
    page.question,
    "",
    "## 最终答案",
    "",
    markdownValue(solve.answer),
    "",
    "## 步骤",
    "",
  ];

  const steps = Array.isArray(solve.steps) ? solve.steps : [];
  if (steps.length) {
    steps.forEach((step, index) => {
      lines.push(`${index + 1}. ${step}`);
    });
  } else {
    lines.push("暂无步骤。");
  }

  if (explanation) {
    lines.push(
      "",
      "## 学生解释",
      "",
      `**总结**：${explanation.summary || ""}`,
      "",
      `**直觉**：${explanation.intuition || ""}`,
      "",
      `**易错点**：${explanation.common_mistake || ""}`,
      "",
      `**自检**：${explanation.self_check_question || ""}`,
    );
  }

  return `${lines.join("\n")}\n`;
}

function downloadText(filename, content) {
  const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function noteFilename(page) {
  const solveId = page.solve.solve_id || "solve";
  const subject = page.solve.subject || "unknown";
  return `examsolver-${subject}-${solveId.slice(0, 8)}.md`;
}

async function markdownArtifact(page) {
  const solveId = page.solve.solve_id;
  if (!solveId) return noteMarkdown(page);

  try {
    const response = await fetch(`/solve/${encodeURIComponent(solveId)}/export.md`, {
      cache: "no-store",
    });
    if (!response.ok) throw new Error("server export unavailable");
    return await response.text();
  } catch {
    return noteMarkdown(page);
  }
}

function resizeComposer() {
  els.input.style.height = "auto";
  els.input.style.height = `${Math.min(Math.max(els.input.scrollHeight, 52), 200)}px`;
}

function currentPage() {
  return state.currentIndex >= 0 ? state.pages[state.currentIndex] : null;
}

function updatePager() {
  const total = state.pages.length;
  els.pageIndicator.textContent = `${total ? state.currentIndex + 1 : 0} / ${total}`;
  els.pagePrev.disabled = state.currentIndex <= 0;
  els.pageNext.disabled = state.currentIndex >= total - 1;
}

function renderCurrentPage() {
  const page = currentPage();
  updatePager();

  if (!page) {
    els.empty.hidden = false;
    els.noteStack.hidden = true;
    els.resultStatus.hidden = true;
    els.pageTools.hidden = true;
    return;
  }

  const solve = page.solve;
  const steps = Array.isArray(solve.steps) ? solve.steps : [];
  const explanation = solve.student_explanation;

  els.empty.hidden = true;
  els.noteStack.hidden = false;
  els.pageTools.hidden = false;
  els.problemSubject.textContent = localize(labels.subject, solve.subject);
  els.problemType.textContent = localize(labels.type, solve.question_type);
  els.problemTime.textContent = formatTime(page.createdAt);
  els.problemText.textContent = page.question;
  els.answerSkill.textContent = solve.skill || "unknown";
  els.answerText.innerHTML = renderMathText(formatAnswer(solve.answer));
  els.stepsMeta.textContent = `${steps.length} 步`;
  setStatus(solve.success ? "success" : "unsupported", solve.message);
  renderSteps(steps);
  renderFormulas(extractLatexSegments(solve.answer, solve.steps, explanation));
  renderExplanation(explanation);
}

function renderSteps(steps) {
  if (!steps.length) {
    els.stepsLayout.innerHTML = '<p class="muted">当前题型还没有可展示步骤。</p>';
    return;
  }

  const active = Math.min(state.activeStepIndex, steps.length - 1);
  state.activeStepIndex = active;
  els.stepsLayout.innerHTML = `
    <nav class="steps-nav">
      ${steps
        .map(
          (step, index) => `
            <button type="button" class="step-nav-item ${index === active ? "step-nav-item-active" : ""}" data-step-index="${index}">
              <span class="step-order">${String(index + 1).padStart(2, "0")}</span>
              <span class="step-label">${escapeHtml(shortStep(step))}</span>
            </button>
          `,
        )
        .join("")}
    </nav>
    <div class="step-detail">
      <p class="step-detail-num">步骤 ${String(active + 1).padStart(2, "0")} / ${steps.length}</p>
      <div class="step-detail-body math">${renderMathText(steps[active])}</div>
    </div>
  `;
}

function renderFormulas(formulas) {
  if (!formulas.length) {
    els.formulasPanel.hidden = true;
    els.formulaList.innerHTML = "";
    els.formulasMeta.textContent = "0 项";
    return;
  }

  els.formulasPanel.hidden = false;
  els.formulasMeta.textContent = `${formulas.length} 项`;
  els.formulaList.innerHTML = formulas
    .map(
      (formula, index) => `
        <div class="formula-item" data-formula-index="${index}">
          <span class="eyebrow">Formula ${String(index + 1).padStart(2, "0")}</span>
          <b class="math" data-formula-source>${escapeHtml(formula)}</b>
          <div class="formula-preview math" data-preview>${renderLatex(formula)}</div>
          <div class="formula-actions">
            <button class="formula-copy-button" type="button" data-copy-formula>复制公式</button>
            <button class="formula-editor-toggle" type="button" data-toggle-formula>
              编辑 LaTeX
            </button>
            <span class="formula-feedback" data-formula-feedback></span>
          </div>
          <label class="formula-editor-field" data-editor-field>
            <span>LaTeX 源码</span>
            <textarea class="formula-editor" spellcheck="false" data-formula-editor>${escapeHtml(formula)}</textarea>
          </label>
        </div>
      `,
    )
    .join("");
}

function renderExplanation(explanation) {
  if (!explanation) {
    els.explanationPanel.hidden = true;
    els.explanationGrid.innerHTML = "";
    return;
  }

  els.explanationPanel.hidden = false;
  els.explanationGrid.innerHTML = [
    ["总结", explanation.summary],
    ["直觉", explanation.intuition],
    ["易错点", explanation.common_mistake],
    ["自检", explanation.self_check_question],
  ]
    .map(
      ([label, value]) => `
        <div class="explanation-item">
          <span>${escapeHtml(label)}</span>
          <p class="math">${renderMathText(value || "")}</p>
        </div>
      `,
    )
    .join("");
}

async function solveQuestion(question) {
  const trimmed = question.trim();
  if (!trimmed || state.busy) return;

  setBusy(true);
  els.empty.hidden = false;
  els.noteStack.hidden = true;
  els.empty.innerHTML = "<p>正在生成解题笔记...</p>";

  try {
    const response = await fetch("/solve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: trimmed }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "请求失败");
    state.pages.push({ question: trimmed, solve: payload, createdAt: new Date().toISOString() });
    state.currentIndex = state.pages.length - 1;
    state.activeStepIndex = 0;
    renderCurrentPage();
    await refreshHistory();
  } catch (error) {
    els.empty.hidden = false;
    els.noteStack.hidden = true;
    els.empty.innerHTML = `<p>${escapeHtml(error.message || "请求失败")}</p>`;
  } finally {
    setBusy(false);
  }
}

async function refreshHistory() {
  try {
    const response = await fetch("/solve/history?limit=20", { cache: "no-store" });
    const page = await response.json();
    const items = Array.isArray(page.items) ? page.items : [];
    if (!items.length) {
      els.history.innerHTML = '<p class="muted">暂无历史</p>';
      return;
    }
    els.history.innerHTML = items
      .map(
        (item) => `
          <button
            class="history-item"
            type="button"
            data-solve-id="${escapeHtml(item.solve_id)}"
            data-question-snippet="${escapeHtml(item.question_snippet || "历史解答")}"
          >
            <strong>${escapeHtml(item.question_snippet || item.solve_id)}</strong>
            <span>${escapeHtml(localize(labels.subject, item.subject))} · ${escapeHtml(localize(labels.type, item.question_type))}</span>
          </button>
        `,
      )
      .join("");
  } catch {
    els.history.innerHTML = '<p class="muted">历史不可用</p>';
  }
}

async function loadSolve(solveId, questionSnippet = "历史解答") {
  if (!solveId || state.busy) return;
  try {
    const response = await fetch(`/solve/${encodeURIComponent(solveId)}`, { cache: "no-store" });
    if (!response.ok) throw new Error("历史解答不存在");
    const payload = await response.json();
    state.pages.push({
      question: questionSnippet,
      solve: payload,
      createdAt: new Date().toISOString(),
    });
    state.currentIndex = state.pages.length - 1;
    state.activeStepIndex = 0;
    renderCurrentPage();
  } catch (error) {
    els.empty.hidden = false;
    els.noteStack.hidden = true;
    els.empty.innerHTML = `<p>${escapeHtml(error.message || "读取失败")}</p>`;
  }
}

function goToPage(delta) {
  const next = state.currentIndex + delta;
  if (next < 0 || next >= state.pages.length) return;
  state.currentIndex = next;
  state.activeStepIndex = 0;
  renderCurrentPage();
}

els.form.addEventListener("submit", (event) => {
  event.preventDefault();
  solveQuestion(els.input.value);
});

els.input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    solveQuestion(els.input.value);
  }
});

els.input.addEventListener("input", resizeComposer);

document.addEventListener("keydown", (event) => {
  const tag = event.target.tagName;
  if (tag === "TEXTAREA" || tag === "INPUT") return;
  if (event.key === "ArrowLeft" || event.key === "ArrowUp") goToPage(-1);
  if (event.key === "ArrowRight" || event.key === "ArrowDown") goToPage(1);
});

els.stepsLayout.addEventListener("click", (event) => {
  const button = event.target.closest("[data-step-index]");
  if (!button) return;
  state.activeStepIndex = Number(button.getAttribute("data-step-index"));
  renderCurrentPage();
});

els.formulaList.addEventListener("click", async (event) => {
  const copyButton = event.target.closest("[data-copy-formula]");
  if (copyButton) {
    const item = copyButton.closest("[data-formula-index]");
    const editor = item.querySelector("[data-formula-editor]");
    const source = item.querySelector("[data-formula-source]");
    const feedback = item.querySelector("[data-formula-feedback]");
    try {
      await copyText(editor.value || source.textContent);
      feedback.textContent = "已复制";
      window.setTimeout(() => {
        feedback.textContent = "";
      }, 1600);
    } catch {
      feedback.textContent = "复制失败";
    }
    return;
  }

  const button = event.target.closest("[data-toggle-formula]");
  if (!button) return;
  const item = button.closest("[data-formula-index]");
  const field = item.querySelector("[data-editor-field]");
  const isOpen = field.getAttribute("data-open") === "true";
  field.setAttribute("data-open", String(!isOpen));
  button.textContent = isOpen ? "编辑 LaTeX" : "收起公式编辑";
});

els.formulaList.addEventListener("input", (event) => {
  const editor = event.target.closest("[data-formula-editor]");
  if (!editor) return;
  const item = editor.closest("[data-formula-index]");
  const preview = item.querySelector("[data-preview]");
  preview.innerHTML = renderLatex(editor.value);
  const source = item.querySelector("[data-formula-source]");
  source.textContent = editor.value;
});

els.pagePrev.addEventListener("click", () => goToPage(-1));
els.pageNext.addEventListener("click", () => goToPage(1));

els.copyAnswer.addEventListener("click", async () => {
  const page = currentPage();
  if (!page) return;
  try {
    await copyText(formatAnswer(page.solve.answer));
    showToolFeedback("答案已复制");
  } catch {
    showToolFeedback("复制失败");
  }
});

els.copyNote.addEventListener("click", async () => {
  const page = currentPage();
  if (!page) return;
  try {
    await copyText(noteMarkdown(page));
    showToolFeedback("笔记已复制");
  } catch {
    showToolFeedback("复制失败");
  }
});

els.downloadNote.addEventListener("click", async () => {
  const page = currentPage();
  if (!page) return;
  downloadText(noteFilename(page), await markdownArtifact(page));
  showToolFeedback("Markdown 已生成");
});

els.exportPdf.addEventListener("click", () => {
  const page = currentPage();
  if (!page) return;
  const solveId = page.solve.solve_id;
  if (!solveId) {
    showToolFeedback("无法导出 PDF：缺少 solve_id");
    return;
  }
  const link = document.createElement("a");
  link.href = `/solve/${encodeURIComponent(solveId)}/export.pdf`;
  link.rel = "noopener";
  document.body.append(link);
  link.click();
  link.remove();
  showToolFeedback("PDF 生成中…");
});

els.history.addEventListener("click", (event) => {
  const button = event.target.closest("[data-solve-id]");
  if (button) {
    loadSolve(
      button.getAttribute("data-solve-id"),
      button.getAttribute("data-question-snippet") || "历史解答",
    );
  }
});

els.newThread.addEventListener("click", () => {
  state.pages = [];
  state.currentIndex = -1;
  state.activeStepIndex = 0;
  els.input.value = "";
  resizeComposer();
  renderCurrentPage();
  els.input.focus();
});

renderCurrentPage();
resizeComposer();
refreshHistory();
