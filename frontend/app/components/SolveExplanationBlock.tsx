import { MathText } from "./MathText";
import { SolveNotePanel } from "./SolveNotePanel";
import type { ExplanationBlockViewModel } from "./solveWorkbenchViewModel";
import styles from "./SolveWorkbench.module.css";

type SolveExplanationBlockProps = {
  block: ExplanationBlockViewModel;
};

export function SolveExplanationBlock({ block }: SolveExplanationBlockProps) {
  return (
    <SolveNotePanel title={block.title}>
      <div className={styles.explanationGrid}>
        {block.items.map((item) => (
          <div key={item.id} className={styles.explanationItem}>
            <span>{item.label}</span>
            <p>
              <MathText text={item.text} />
            </p>
          </div>
        ))}
      </div>
    </SolveNotePanel>
  );
}
