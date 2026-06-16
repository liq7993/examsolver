"use client";

import { useEffect } from "react";
import { MathText } from "./MathText";
import { SolveNotePanel } from "./SolveNotePanel";
import type { StepItemViewModel, StepsBlockViewModel } from "./solveWorkbenchViewModel";
import styles from "./SolveWorkbench.module.css";

function stepShortLabel(text: string, max = 36): string {
  const cleaned = text
    .replace(/\f\s*rac/g, "frac")
    .replace(/�\s*rac/g, "frac")
    .replace(/\t\s*ext\s*\{\s*([^}]+?)\s*\}/g, "$1")
    .replace(/\t\s*ext\s+([A-Za-z]+)/g, "$1")
    .replace(/\bext\s*\{\s*([^}]+?)\s*\}/g, "$1")
    .replace(/\bext\s*(N|kN|m|s|kg)\b/g, "$1")
    .replace(/\\CIRC\b/g, "°")
    .replace(/\\c(?:irc)?\$/gi, "°")
    .replace(/\$/g, "");
  const first = cleaned.split(/[。！？.!?\n]/)[0] ?? cleaned;
  return first.length > max ? first.slice(0, max) + "…" : first;
}

export function SolveStepsBlock({
  block,
  activeStepId,
  setActiveStepId,
}: {
  block: StepsBlockViewModel;
  activeStepId: string | null;
  setActiveStepId: (id: string) => void;
}) {
  const firstId = block.items[0]?.id ?? null;
  const resolvedId = activeStepId ?? firstId;
  const activeStep: StepItemViewModel | null =
    block.items.find((s) => s.id === resolvedId) ?? block.items[0] ?? null;

  useEffect(() => {
    if (!activeStepId && firstId) setActiveStepId(firstId);
  }, [activeStepId, firstId, setActiveStepId]);

  return (
    <SolveNotePanel title={block.title} meta={block.meta}>
      <div className={styles.stepsLayout}>
        {/* Left: compact step list */}
        <nav className={styles.stepsNav}>
          {block.items.map((step) => (
            <button
              key={step.id}
              type="button"
              className={`${styles.stepNavItem} ${step.id === resolvedId ? styles.stepNavItemActive : ""}`}
              onClick={() => setActiveStepId(step.id)}
            >
              <span className={styles.stepNavOrder}>{step.orderLabel}</span>
              <span className={styles.stepNavLabel}>{stepShortLabel(step.explanation)}</span>
            </button>
          ))}
        </nav>

        {/* Right: step detail */}
        {activeStep && (
          <div className={styles.stepDetail}>
            <p className={styles.stepDetailNum}>
              步骤 {activeStep.orderLabel} / {block.items.length}
            </p>
            <div className={styles.stepDetailBody}>
              <MathText text={activeStep.explanation} />
            </div>
            {activeStep.formulas.length > 0 && (
              <div className={styles.formulaList}>
                {activeStep.formulas.map((f) => (
                  <div key={f.id} className={styles.formulaItem}>
                    <b>{f.label}</b>
                    <MathText text={f.latex ?? f.text} display />
                  </div>
                ))}
              </div>
            )}
            {activeStep.selfCheckLabel && (
              <p className={styles.stepHint}>{activeStep.selfCheckLabel}</p>
            )}
          </div>
        )}
      </div>
    </SolveNotePanel>
  );
}
