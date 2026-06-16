import { SolveNotePanel } from "./SolveNotePanel";
import type { ProblemBlockViewModel } from "./solveWorkbenchViewModel";
import styles from "./SolveWorkbench.module.css";

type SolveProblemBlockProps = {
  block: ProblemBlockViewModel;
};

export function SolveProblemBlock({ block }: SolveProblemBlockProps) {
  return (
    <SolveNotePanel title="">
      <div className={styles.problemHeader}>
        <h1>{block.subjectLabel}</h1>
        <h2>{block.questionTypeLabel}</h2>
        <h3>{block.title}</h3>
        <time>{block.generatedAtLabel}</time>
        <p>{block.text}</p>
      </div>
    </SolveNotePanel>
  );
}
