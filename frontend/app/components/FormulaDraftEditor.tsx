"use client";

import { useMemo, useState } from "react";
import { renderFormulaHtml, renderMathTextHtml } from "./mathRendering";
import styles from "./SolveWorkbench.module.css";

type FormulaDraftEditorProps = {
  label: string;
  sourceText: string;
  initialValue: string;
};

function renderDraft(draft: string) {
  if (draft.includes("$") || draft.includes("\\(") || draft.includes("\\[")) {
    return renderMathTextHtml(draft);
  }

  return renderFormulaHtml(draft, true);
}

export function FormulaDraftEditor({
  label,
  sourceText,
  initialValue,
}: FormulaDraftEditorProps) {
  const [draft, setDraft] = useState(initialValue);
  const [isEditing, setIsEditing] = useState(false);
  const rendered = useMemo(() => renderDraft(draft), [draft]);

  return (
    <div className={styles.formulaEditorShell}>
      <div
        className={styles.formulaPreview}
        dangerouslySetInnerHTML={{ __html: rendered.html }}
      />
      {rendered.error ? <p className={styles.formulaError}>公式渲染失败：{rendered.error}</p> : null}
      {sourceText !== initialValue ? <p className={styles.formulaSource}>原式：{sourceText}</p> : null}
      <button
        className={styles.formulaEditorToggle}
        type="button"
        onClick={() => setIsEditing((value) => !value)}
      >
        {isEditing ? "收起公式编辑" : "编辑 LaTeX"}
      </button>
      {isEditing ? (
        <label className={styles.formulaEditorField}>
          <span>LaTeX 源码</span>
          <textarea
            className={styles.formulaEditor}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            aria-label={`${label} 公式草稿`}
            spellCheck={false}
          />
        </label>
      ) : null}
    </div>
  );
}
