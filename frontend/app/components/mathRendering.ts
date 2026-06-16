import katex from "katex";

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function normalizeMathSource(value: string): string {
  return value
    .replace(/\f\s*rac/g, "\\frac")
    .replace(/�\s*rac/g, "\\frac")
    .replace(/\t\s*ext\s*\{\s*([^}]+?)\s*\}/g, "\\text{$1}")
    .replace(/\t\s*ext\s+([A-Za-z]+)/g, "\\text{$1}")
    .replace(/\bext\s*\{\s*([^}]+?)\s*\}/g, "\\text{$1}")
    .replace(/\bext\s*(N|kN|m|s|kg)\b/g, "\\text{$1}")
    .replace(/\\CIRC\b/g, "\\circ")
    .replace(/\\c(?:irc)?\$/gi, "\\circ")
    .replace(/\bCIRC\b/g, "\\circ");
}

function stripOuterMathDelimiters(value: string): string {
  const trimmed = value.trim();
  if (trimmed.startsWith("$$") && trimmed.endsWith("$$") && trimmed.length >= 4) {
    return trimmed.slice(2, -2).trim();
  }
  if (trimmed.startsWith("$") && trimmed.endsWith("$") && trimmed.length >= 2) {
    return trimmed.slice(1, -1).trim();
  }
  if (trimmed.startsWith("\\[") && trimmed.endsWith("\\]")) {
    return trimmed.slice(2, -2).trim();
  }
  if (trimmed.startsWith("\\(") && trimmed.endsWith("\\)")) {
    return trimmed.slice(2, -2).trim();
  }
  return trimmed;
}

function hasBalancedDollarMath(value: string): boolean {
  const dollarCount = (value.match(/\$/g) ?? []).length;
  return dollarCount > 1 && dollarCount % 2 === 0;
}

export function renderFormulaHtml(
  source: string,
  displayMode = true,
): { html: string; error: string } {
  try {
    const normalizedSource = stripOuterMathDelimiters(normalizeMathSource(source));

    return {
      html: katex.renderToString(normalizedSource.trim() || "\\ ", {
        throwOnError: false,
        displayMode,
        output: "html",
      }),
      error: "",
    };
  } catch (error) {
    return {
      html: "",
      error: error instanceof Error ? error.message : "公式渲染失败",
    };
  }
}

export function renderMathTextHtml(source: string): { html: string; error: string } {
  try {
    const normalized = normalizeMathSource(source)
      .replaceAll("\\(", "$")
      .replaceAll("\\)", "$")
      .replaceAll("\\[", "$$")
      .replaceAll("\\]", "$$");
    const pattern = /\$\$([\s\S]+?)\$\$|\$([^$\n]+?)\$/g;
    let lastIndex = 0;
    let html = "";
    let match: RegExpExecArray | null;

    while ((match = pattern.exec(normalized)) !== null) {
      html += escapeHtml(normalized.slice(lastIndex, match.index)).replaceAll("\n", "<br />");
      html += katex.renderToString(match[1] ?? match[2] ?? "", {
        throwOnError: false,
        displayMode: Boolean(match[1]),
        output: "html",
      });
      lastIndex = pattern.lastIndex;
    }

    html += escapeHtml(normalized.slice(lastIndex)).replaceAll("\n", "<br />");

    return { html, error: "" };
  } catch (error) {
    return {
      html: escapeHtml(source).replaceAll("\n", "<br />"),
      error: error instanceof Error ? error.message : "公式渲染失败",
    };
  }
}

function isLooseMathSegment(value: string): boolean {
  const trimmed = value.trim();

  if (trimmed.length === 0) {
    return false;
  }

  return (
    /\\(?:frac|sqrt|sum|sin|cos|tan|cot|cdot|times|text|circ|theta|alpha|beta|gamma)/.test(trimmed) ||
    /[A-Za-z]_\{?[A-Za-z0-9]+\}?/.test(trimmed) ||
    /[A-Za-z]\^\{?[A-Za-z0-9]+\}?/.test(trimmed) ||
    /[=∑≈≤≥±]/.test(trimmed)
  );
}

export function renderLooseMathTextHtml(source: string): { html: string; error: string } {
  const normalizedSource = normalizeMathSource(source);
  const looseSource = hasBalancedDollarMath(normalizedSource)
    ? normalizedSource
    : normalizedSource.replaceAll("$", "");

  if (
    hasBalancedDollarMath(normalizedSource) ||
    normalizedSource.includes("\\(") ||
    normalizedSource.includes("\\[")
  ) {
    return renderMathTextHtml(normalizedSource);
  }

  const candidatePattern =
    /(?:\\[A-Za-z]+|\\[{}]|[A-Za-z0-9_{}()[\]^+\-*/=<>.°∑≈≤≥±]|[ \t])+/g;
  let lastIndex = 0;
  let html = "";
  let firstError = "";
  let match: RegExpExecArray | null;

  while ((match = candidatePattern.exec(looseSource)) !== null) {
    const candidate = match[0];
    html += escapeHtml(looseSource.slice(lastIndex, match.index)).replaceAll("\n", "<br />");

    if (isLooseMathSegment(candidate)) {
      const rendered = renderFormulaHtml(candidate.trim(), false);
      html += rendered.html || escapeHtml(candidate);
      firstError ||= rendered.error;
    } else {
      html += escapeHtml(candidate).replaceAll("\n", "<br />");
    }

    lastIndex = candidatePattern.lastIndex;
  }

  html += escapeHtml(looseSource.slice(lastIndex)).replaceAll("\n", "<br />");

  return {
    html,
    error: firstError,
  };
}
