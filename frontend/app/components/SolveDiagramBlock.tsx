"use client";

import { useState } from "react";
import { SolveDiagramCanvas } from "./SolveDiagramCanvas";
import type { DiagramBlockViewModel } from "./solveWorkbenchViewModel";
import styles from "./SolveWorkbench.module.css";

type SolveDiagramBlockProps = {
  block: DiagramBlockViewModel;
  activeStepId: string | null;
};

export function SolveDiagramBlock({ block, activeStepId }: SolveDiagramBlockProps) {
  const [isOpen, setIsOpen] = useState(true);
  return (
    <section className={styles.panel}>
      <button
        type="button"
        className={styles.diagramToggleHeader}
        onClick={() => setIsOpen((v) => !v)}
        aria-expanded={isOpen}
      >
        <span className={styles.diagramToggleTitle}>{block.title}</span>
        <span className={styles.diagramToggleMeta}>{block.meta}</span>
        <span className={styles.diagramChevron} aria-hidden>
          {isOpen ? "▲" : "▼"}
        </span>
      </button>

      {isOpen && (
        <div className={styles.diagramFrameResizable}>
          <SolveDiagramCanvas block={block} activeStepId={activeStepId} />
        </div>
      )}
    </section>
  );
}
