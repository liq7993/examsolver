const state = {
  pages: [],
  currentIndex: -1,
  activeStepIndex: 0,
  busy: false,
  settings: { provider: "", providers: [] },
  capabilities: [],
  historyItems: [],
  activeSubject: null,
  mistakesOpen: false,
  mistakes: [],
};

const ONBOARDED_KEY = "examsolver:onboarded";
const SIDEBAR_KEY = "examsolver:sidebar-collapsed";
// "general" is the catch-all fallback skill, not a study subject, so it is
// hidden from the homepage project cards.
const HIDDEN_CARD_SUBJECTS = new Set(["general"]);

const els = {
  form: document.querySelector("#solve-form"),
  input: document.querySelector("#question-input"),
  submit: document.querySelector("#submit-button"),
  empty: document.querySelector("#empty-page"),
  subjectCards: document.querySelector("#subject-cards"),
  projectView: document.querySelector("#project-view"),
  projectBack: document.querySelector("#project-back"),
  projectTitle: document.querySelector("#project-title"),
  projectSub: document.querySelector("#project-sub"),
  projectList: document.querySelector("#project-list"),
  openMistakes: document.querySelector("#open-mistakes"),
  mistakesView: document.querySelector("#mistakes-view"),
  mistakesBack: document.querySelector("#mistakes-back"),
  mistakesExport: document.querySelector("#mistakes-export"),
  mistakesSub: document.querySelector("#mistakes-sub"),
  mistakesList: document.querySelector("#mistakes-list"),
  addMistake: document.querySelector("#add-mistake"),
  pageFlash: document.querySelector("#page-flash"),
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
  plotPanel: document.querySelector("#plot-panel"),
  plotMeta: document.querySelector("#plot-meta"),
  plotBody: document.querySelector("#plot-body"),
  formulasPanel: document.querySelector("#formulas-panel"),
  formulasMeta: document.querySelector("#formulas-meta"),
  formulaList: document.querySelector("#formula-list"),
  explanationPanel: document.querySelector("#explanation-panel"),
  explanationGrid: document.querySelector("#explanation-grid"),
  history: document.querySelector("#history-list"),
  newThread: document.querySelector("#new-thread"),
  openSettings: document.querySelector("#open-settings"),
  closeSettings: document.querySelector("#close-settings"),
  settingsOverlay: document.querySelector("#settings-overlay"),
  providerSelect: document.querySelector("#provider-select"),
  apiKeyField: document.querySelector("#api-key-field"),
  apiKeyInput: document.querySelector("#api-key-input"),
  apiKeyState: document.querySelector("#api-key-state"),
  saveSettings: document.querySelector("#save-settings"),
  settingsFeedback: document.querySelector("#settings-feedback"),
  tutorialOverlay: document.querySelector("#tutorial-overlay"),
  tutorialOpenSettings: document.querySelector("#tutorial-open-settings"),
  tutorialDismiss: document.querySelector("#tutorial-dismiss"),
  appShell: document.querySelector(".app-shell"),
  collapseSidebar: document.querySelector("#collapse-sidebar"),
  expandSidebar: document.querySelector("#expand-sidebar"),
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
  els.pageFlash.hidden = true;

  if (!page) {
    els.noteStack.hidden = true;
    els.resultStatus.hidden = true;
    els.pageTools.hidden = true;
    if (state.mistakesOpen) {
      els.empty.hidden = true;
      els.projectView.hidden = true;
      els.mistakesView.hidden = false;
      renderMistakes();
    } else if (state.activeSubject) {
      els.empty.hidden = true;
      els.mistakesView.hidden = true;
      els.projectView.hidden = false;
      renderProjectView();
    } else {
      els.empty.hidden = false;
      els.projectView.hidden = true;
      els.mistakesView.hidden = true;
    }
    return;
  }

  const solve = page.solve;
  const steps = Array.isArray(solve.steps) ? solve.steps : [];
  const explanation = solve.student_explanation;

  els.empty.hidden = true;
  els.projectView.hidden = true;
  els.mistakesView.hidden = true;
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
  renderPlot(solve.plot);
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

const PLOT_COLORS = ["#0a84ff", "#ff6a00", "#34c759", "#af52de"];

// Split a sampled curve where the backend skipped points (e.g. across an
// asymptote) so we never draw a spurious vertical line through a gap.
function plotSegments(points) {
  if (points.length < 2) return [];
  const deltas = [];
  for (let i = 1; i < points.length; i += 1) deltas.push(points[i][0] - points[i - 1][0]);
  const sorted = [...deltas].sort((a, b) => a - b);
  const median = sorted[Math.floor(sorted.length / 2)] || 0;
  const threshold = median > 0 ? median * 2.5 : Infinity;
  const segments = [];
  let current = [points[0]];
  for (let i = 1; i < points.length; i += 1) {
    if (points[i][0] - points[i - 1][0] > threshold) {
      if (current.length >= 2) segments.push(current);
      current = [points[i]];
    } else {
      current.push(points[i]);
    }
  }
  if (current.length >= 2) segments.push(current);
  return segments;
}

function plotNumber(value) {
  const rounded = Math.round(value * 100) / 100;
  return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(2);
}

function buildPlotSvg(plot) {
  const series = plot.series;
  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;
  series.forEach((line) =>
    line.points.forEach(([x, y]) => {
      if (x < minX) minX = x;
      if (x > maxX) maxX = x;
      if (y < minY) minY = y;
      if (y > maxY) maxY = y;
    }),
  );
  if (!Number.isFinite(minX) || !Number.isFinite(minY)) return "";
  if (minX === maxX) {
    minX -= 1;
    maxX += 1;
  }
  if (minY === maxY) {
    minY -= 1;
    maxY += 1;
  }
  const padY = (maxY - minY) * 0.08;
  minY -= padY;
  maxY += padY;

  const width = 560;
  const height = 360;
  const ml = 48;
  const mr = 18;
  const mt = 18;
  const mb = 34;
  const iw = width - ml - mr;
  const ih = height - mt - mb;
  const sx = (x) => ml + ((x - minX) / (maxX - minX)) * iw;
  const sy = (y) => mt + (1 - (y - minY) / (maxY - minY)) * ih;

  const parts = [`<rect class="plot-frame" x="${ml}" y="${mt}" width="${iw}" height="${ih}" />`];
  if (minY <= 0 && maxY >= 0) {
    const y0 = sy(0).toFixed(1);
    parts.push(`<line class="plot-axis" x1="${ml}" y1="${y0}" x2="${ml + iw}" y2="${y0}" />`);
  }
  if (minX <= 0 && maxX >= 0) {
    const x0 = sx(0).toFixed(1);
    parts.push(`<line class="plot-axis" x1="${x0}" y1="${mt}" x2="${x0}" y2="${mt + ih}" />`);
  }
  series.forEach((line, index) => {
    const color = PLOT_COLORS[index % PLOT_COLORS.length];
    plotSegments(line.points).forEach((segment) => {
      const pts = segment.map(([x, y]) => `${sx(x).toFixed(1)},${sy(y).toFixed(1)}`).join(" ");
      parts.push(`<polyline class="plot-curve" stroke="${color}" points="${pts}" />`);
    });
  });
  parts.push(
    `<text class="plot-tick" x="${ml}" y="${mt + ih + 18}" text-anchor="start">${escapeHtml(plotNumber(minX))}</text>`,
    `<text class="plot-tick" x="${ml + iw}" y="${mt + ih + 18}" text-anchor="end">${escapeHtml(plotNumber(maxX))}</text>`,
    `<text class="plot-tick" x="${ml - 6}" y="${mt + 10}" text-anchor="end">${escapeHtml(plotNumber(maxY))}</text>`,
    `<text class="plot-tick" x="${ml - 6}" y="${mt + ih}" text-anchor="end">${escapeHtml(plotNumber(minY))}</text>`,
    `<text class="plot-axis-name" x="${ml + iw}" y="${mt + ih + 30}" text-anchor="end">${escapeHtml(plot.x_label || "x")}</text>`,
    `<text class="plot-axis-name" x="${ml - 6}" y="${mt - 4}" text-anchor="end">${escapeHtml(plot.y_label || "y")}</text>`,
  );
  const labelWidth = Math.max(...series.map((line) => String(line.label).length));
  const legendW = 30 + labelWidth * 9;
  const legendH = series.length * 18 + 8;
  parts.push(
    `<rect class="plot-legend-bg" x="${ml + 6}" y="${mt + 6}" width="${legendW}" height="${legendH}" rx="6" />`,
  );
  series.forEach((line, index) => {
    const color = PLOT_COLORS[index % PLOT_COLORS.length];
    const lx = ml + 14;
    const ly = mt + 20 + index * 18;
    parts.push(
      `<rect x="${lx}" y="${ly - 9}" width="12" height="12" rx="2" fill="${color}" />` +
        `<text class="plot-legend-text" x="${lx + 18}" y="${ly + 1}">${escapeHtml(line.label)}</text>`,
    );
  });

  return (
    `<svg class="plot-svg" viewBox="0 0 ${width} ${height}" role="img" ` +
    `aria-label="${escapeHtml(plot.title || "函数图像")}" preserveAspectRatio="xMidYMid meet">` +
    `${parts.join("")}</svg>`
  );
}

function renderPlot(plot) {
  const series =
    plot && Array.isArray(plot.series)
      ? plot.series.filter((line) => Array.isArray(line.points) && line.points.length >= 2)
      : [];
  if (!plot || !series.length) {
    els.plotPanel.hidden = true;
    els.plotBody.innerHTML = "";
    els.plotMeta.textContent = "0 条曲线";
    return;
  }
  els.plotPanel.hidden = false;
  els.plotMeta.textContent = `${series.length} 条曲线`;
  els.plotBody.innerHTML = buildPlotSvg({ ...plot, series });
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
  els.empty.hidden = true;
  els.projectView.hidden = true;
  els.mistakesView.hidden = true;
  state.mistakesOpen = false;
  els.noteStack.hidden = true;
  els.pageFlash.hidden = false;
  els.pageFlash.textContent = "正在生成解题笔记…";

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
    els.pageFlash.hidden = false;
    els.pageFlash.textContent = error.message || "请求失败";
  } finally {
    setBusy(false);
  }
}

function renderHistory() {
  const items = state.historyItems;
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
}

async function refreshHistory() {
  try {
    const response = await fetch("/solve/history?limit=100", { cache: "no-store" });
    const page = await response.json();
    state.historyItems = Array.isArray(page.items) ? page.items : [];
  } catch {
    state.historyItems = [];
    els.history.innerHTML = '<p class="muted">历史不可用</p>';
    renderSubjectCards();
    return;
  }
  renderHistory();
  renderSubjectCards();
  if (state.activeSubject && !currentPage()) renderProjectView();
}

function subjectSolvedCount(subject) {
  return state.historyItems.filter((item) => (item.subject || "unknown") === subject).length;
}

function subjectNotes(subject) {
  return state.historyItems.filter((item) => (item.subject || "unknown") === subject);
}

function renderSubjectCards() {
  const subjects = state.capabilities.filter((item) => !HIDDEN_CARD_SUBJECTS.has(item.name));
  if (!subjects.length) {
    els.subjectCards.innerHTML = '<p class="muted">科目加载中…</p>';
    return;
  }
  els.subjectCards.innerHTML = subjects
    .map((subject) => {
      const types = Array.isArray(subject.question_types) ? subject.question_types : [];
      const typeLabels = types.map((type) => localize(labels.type, type)).join(" · ") || "通用解答";
      const count = subjectSolvedCount(subject.name);
      return `
        <button class="subject-card" type="button" data-subject="${escapeHtml(subject.name)}">
          <span class="subject-card-name">${escapeHtml(localize(labels.subject, subject.name))}</span>
          <span class="subject-card-types">${escapeHtml(typeLabels)}</span>
          <span class="subject-card-count">${count} 条解答</span>
        </button>
      `;
    })
    .join("");
}

async function loadCapabilities() {
  try {
    const response = await fetch("/solve/capabilities", { cache: "no-store" });
    if (!response.ok) throw new Error("capabilities unavailable");
    const data = await response.json();
    state.capabilities = Array.isArray(data.subjects) ? data.subjects : [];
  } catch {
    state.capabilities = [];
  }
  renderSubjectCards();
}

function renderProjectView() {
  const subject = state.activeSubject;
  if (!subject) return;
  els.projectTitle.textContent = localize(labels.subject, subject);
  const capability = state.capabilities.find((item) => item.name === subject);
  const types = capability && Array.isArray(capability.question_types) ? capability.question_types : [];
  const typeLabels = types.map((type) => localize(labels.type, type)).join(" · ");
  els.projectSub.textContent = typeLabels ? `支持题型：${typeLabels}` : "";

  const notes = subjectNotes(subject);
  if (!notes.length) {
    els.projectList.innerHTML = '<p class="muted">还没有该科目的解答，直接输入一道题开始。</p>';
    return;
  }
  els.projectList.innerHTML = notes
    .map(
      (item) => `
        <button
          class="project-item"
          type="button"
          data-solve-id="${escapeHtml(item.solve_id)}"
          data-question-snippet="${escapeHtml(item.question_snippet || "历史解答")}"
        >
          <strong>${escapeHtml(item.question_snippet || item.solve_id)}</strong>
          <span>${escapeHtml(localize(labels.type, item.question_type))} · ${escapeHtml(formatTime(item.created_at))}</span>
        </button>
      `,
    )
    .join("");
}

function openSubjectProject(subject) {
  state.activeSubject = subject;
  renderCurrentPage();
}

function closeSubjectProject() {
  state.activeSubject = null;
  renderCurrentPage();
}

async function loadMistakes() {
  try {
    const response = await fetch("/mistakes", { cache: "no-store" });
    if (!response.ok) throw new Error("mistakes unavailable");
    const data = await response.json();
    state.mistakes = Array.isArray(data) ? data : [];
  } catch {
    state.mistakes = [];
    els.mistakesList.innerHTML = '<p class="muted">错题本不可用</p>';
    els.mistakesSub.textContent = "";
    return;
  }
  renderMistakes();
}

function renderMistakes() {
  const items = state.mistakes;
  els.mistakesSub.textContent = items.length ? `${items.length} 道错题` : "";
  if (!items.length) {
    els.mistakesList.innerHTML =
      '<p class="muted">还没有错题。在任意解答页点「加入错题本」。</p>';
    return;
  }
  els.mistakesList.innerHTML = items
    .map(
      (item) => `
        <article class="mistake-item" data-mistake-id="${escapeHtml(item.id)}">
          <button
            class="mistake-open"
            type="button"
            data-solve-id="${escapeHtml(item.solve_id)}"
            data-question-snippet="错题回顾"
          >
            <strong>${escapeHtml(localize(labels.subject, item.subject))} · ${escapeHtml(localize(labels.type, item.question_type))}</strong>
            <span>${escapeHtml(formatTime(item.created_at))} · 复习 ${Number(item.review_count) || 0} 次</span>
          </button>
          <label class="mistake-note-field">
            <span>错因笔记</span>
            <textarea class="mistake-note" data-mistake-note spellcheck="false" placeholder="写下错因或思路…">${escapeHtml(item.user_note || "")}</textarea>
          </label>
          <div class="mistake-actions">
            <button type="button" data-save-note>保存笔记</button>
            <button type="button" data-delete-mistake>删除</button>
            <span class="mistake-feedback" data-mistake-feedback></span>
          </div>
        </article>
      `,
    )
    .join("");
}

function openMistakes() {
  state.mistakesOpen = true;
  state.activeSubject = null;
  state.pages = [];
  state.currentIndex = -1;
  renderCurrentPage();
  loadMistakes();
}

function closeMistakes() {
  state.mistakesOpen = false;
  renderCurrentPage();
}

async function addCurrentMistake() {
  const page = currentPage();
  if (!page) return;
  const solveId = page.solve.solve_id;
  if (!solveId) {
    showToolFeedback("无法加入：缺少 solve_id");
    return;
  }
  try {
    const response = await fetch("/mistakes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ solve_id: solveId }),
    });
    if (!response.ok) throw new Error("加入失败");
    state.mistakes = [];
    showToolFeedback("已加入错题本");
  } catch (error) {
    showToolFeedback(error.message || "加入失败");
  }
}

async function saveMistakeNote(mistakeId, note, feedback) {
  try {
    const response = await fetch(`/mistakes/${encodeURIComponent(mistakeId)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_note: note }),
    });
    if (!response.ok) throw new Error("保存失败");
    const updated = await response.json();
    state.mistakes = state.mistakes.map((item) => (item.id === mistakeId ? updated : item));
    if (feedback) feedback.textContent = "已保存";
  } catch (error) {
    if (feedback) feedback.textContent = error.message || "保存失败";
  } finally {
    if (feedback) {
      window.setTimeout(() => {
        feedback.textContent = "";
      }, 1600);
    }
  }
}

async function deleteMistake(mistakeId) {
  try {
    const response = await fetch(`/mistakes/${encodeURIComponent(mistakeId)}`, {
      method: "DELETE",
    });
    if (!response.ok) throw new Error("删除失败");
    state.mistakes = state.mistakes.filter((item) => item.id !== mistakeId);
    renderMistakes();
  } catch {
    // keep the list as-is so the user can retry
  }
}

async function exportMistakes() {
  try {
    const response = await fetch("/mistakes/export.md", { cache: "no-store" });
    if (!response.ok) throw new Error("导出失败");
    downloadText("examsolver-mistakes.md", await response.text());
  } catch {
    els.mistakesSub.textContent = "导出失败";
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

function providerById(name) {
  return state.settings.providers.find((item) => item.name === name) || null;
}

function describeKeyState(provider) {
  if (!provider) return "";
  if (!provider.requires_key) return "无需 API key";
  if (provider.key_set) return `已配置 · ${provider.key_masked || "已保存"}`;
  return "尚未配置 API key";
}

function syncApiKeyField() {
  const provider = providerById(els.providerSelect.value);
  const requiresKey = provider ? provider.requires_key : true;
  els.apiKeyField.hidden = !requiresKey;
  els.apiKeyInput.value = "";
  if (provider && provider.requires_key && provider.key_set) {
    els.apiKeyInput.placeholder = `已保存 ${provider.key_masked || ""}，留空则保持不变`;
  } else {
    els.apiKeyInput.placeholder = "粘贴 API key";
  }
  els.apiKeyState.textContent = describeKeyState(provider);
}

function renderSettings() {
  const { providers, provider } = state.settings;
  els.providerSelect.innerHTML = providers
    .map((item) => `<option value="${escapeHtml(item.name)}">${escapeHtml(item.label)}</option>`)
    .join("");
  if (provider) els.providerSelect.value = provider;
  syncApiKeyField();
}

function applySettingsPayload(data) {
  state.settings = {
    provider: data.provider || "",
    providers: Array.isArray(data.providers) ? data.providers : [],
  };
  renderSettings();
}

async function loadConfig() {
  try {
    const response = await fetch("/config", { cache: "no-store" });
    if (!response.ok) throw new Error("读取设置失败");
    applySettingsPayload(await response.json());
  } catch (error) {
    els.settingsFeedback.textContent = error.message || "读取设置失败";
  }
}

function openSettings() {
  els.settingsOverlay.hidden = false;
  els.settingsFeedback.textContent = "";
  renderSettings();
  els.providerSelect.focus();
}

function closeSettings() {
  els.settingsOverlay.hidden = true;
}

async function saveSettings() {
  const provider = els.providerSelect.value;
  if (!provider) return;
  const apiKey = els.apiKeyInput.value.trim();
  els.saveSettings.disabled = true;
  els.settingsFeedback.textContent = "保存中…";
  try {
    const response = await fetch("/config", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ provider, api_key: apiKey || null }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "保存失败");
    applySettingsPayload(data);
    els.settingsFeedback.textContent = "已保存，立即生效";
  } catch (error) {
    els.settingsFeedback.textContent = error.message || "保存失败";
  } finally {
    els.saveSettings.disabled = false;
  }
}

function applySidebarState(collapsed) {
  els.appShell.classList.toggle("sidebar-collapsed", collapsed);
  els.expandSidebar.hidden = !collapsed;
  els.collapseSidebar.setAttribute("aria-expanded", String(!collapsed));
}

function setSidebar(collapsed) {
  applySidebarState(collapsed);
  try {
    window.localStorage.setItem(SIDEBAR_KEY, collapsed ? "1" : "0");
  } catch {
    // localStorage unavailable; state simply won't persist across reloads.
  }
}

function initSidebar() {
  let collapsed = false;
  try {
    collapsed = window.localStorage.getItem(SIDEBAR_KEY) === "1";
  } catch {
    collapsed = false;
  }
  applySidebarState(collapsed);
}

function maybeShowTutorial() {
  let onboarded = null;
  try {
    onboarded = window.localStorage.getItem(ONBOARDED_KEY);
  } catch {
    onboarded = null;
  }
  if (!onboarded) els.tutorialOverlay.hidden = false;
}

function dismissTutorial() {
  els.tutorialOverlay.hidden = true;
  try {
    window.localStorage.setItem(ONBOARDED_KEY, "1");
  } catch {
    // localStorage unavailable (e.g. private mode); tutorial reappears next load.
  }
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
  state.activeSubject = null;
  state.mistakesOpen = false;
  els.input.value = "";
  resizeComposer();
  renderCurrentPage();
  els.input.focus();
});

els.subjectCards.addEventListener("click", (event) => {
  const card = event.target.closest("[data-subject]");
  if (!card) return;
  openSubjectProject(card.getAttribute("data-subject"));
});

els.projectBack.addEventListener("click", closeSubjectProject);

els.projectList.addEventListener("click", (event) => {
  const button = event.target.closest("[data-solve-id]");
  if (!button) return;
  loadSolve(
    button.getAttribute("data-solve-id"),
    button.getAttribute("data-question-snippet") || "历史解答",
  );
});

els.openMistakes.addEventListener("click", openMistakes);
els.mistakesBack.addEventListener("click", closeMistakes);
els.mistakesExport.addEventListener("click", exportMistakes);
els.addMistake.addEventListener("click", addCurrentMistake);

els.mistakesList.addEventListener("click", (event) => {
  const openButton = event.target.closest("[data-solve-id]");
  if (openButton) {
    loadSolve(
      openButton.getAttribute("data-solve-id"),
      openButton.getAttribute("data-question-snippet") || "错题回顾",
    );
    return;
  }
  const saveButton = event.target.closest("[data-save-note]");
  if (saveButton) {
    const item = saveButton.closest("[data-mistake-id]");
    const id = item.getAttribute("data-mistake-id");
    const note = item.querySelector("[data-mistake-note]").value;
    const feedback = item.querySelector("[data-mistake-feedback]");
    saveMistakeNote(id, note, feedback);
    return;
  }
  const deleteButton = event.target.closest("[data-delete-mistake]");
  if (deleteButton) {
    const item = deleteButton.closest("[data-mistake-id]");
    deleteMistake(item.getAttribute("data-mistake-id"));
  }
});

els.openSettings.addEventListener("click", openSettings);
els.closeSettings.addEventListener("click", closeSettings);
els.saveSettings.addEventListener("click", saveSettings);
els.providerSelect.addEventListener("change", syncApiKeyField);
els.settingsOverlay.addEventListener("click", (event) => {
  if (event.target === els.settingsOverlay) closeSettings();
});

els.tutorialDismiss.addEventListener("click", dismissTutorial);
els.tutorialOpenSettings.addEventListener("click", () => {
  dismissTutorial();
  openSettings();
});

els.collapseSidebar.addEventListener("click", () => setSidebar(true));
els.expandSidebar.addEventListener("click", () => setSidebar(false));

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !els.settingsOverlay.hidden) closeSettings();
});

renderCurrentPage();
resizeComposer();
refreshHistory();
loadCapabilities();
loadConfig();
initSidebar();
maybeShowTutorial();
