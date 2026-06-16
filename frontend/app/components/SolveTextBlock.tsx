import { MathText } from "./MathText";
import { SolveNotePanel } from "./SolveNotePanel";
import type { TextBlockViewModel } from "./solveWorkbenchViewModel";
import styles from "./SolveWorkbench.module.css";

type SolveTextBlockProps = {
  block: TextBlockViewModel;
};

export function SolveTextBlock({ block }: SolveTextBlockProps) {
  return (
    <SolveNotePanel title={block.title}>
      <div className={styles.detailBody}>
        <p>
          <MathText text={block.text} />
        </p>
      </div>
    </SolveNotePanel>
  );
}
