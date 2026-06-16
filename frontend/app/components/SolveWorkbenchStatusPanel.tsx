import { SolveNotePanel } from "./SolveNotePanel";
import styles from "./SolveWorkbench.module.css";

type SolveWorkbenchStatusPanelProps = {
  message: string;
  tone?: "default" | "error";
};

export function SolveWorkbenchStatusPanel({
  message,
  tone = "default",
}: SolveWorkbenchStatusPanelProps) {
  return (
    <SolveNotePanel title="工作区状态">
      <div className={styles.detailBody}>
        <p className={tone === "error" ? styles.errorText : undefined}>{message}</p>
      </div>
    </SolveNotePanel>
  );
}
