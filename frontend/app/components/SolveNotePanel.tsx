import type { ReactNode } from "react";
import styles from "./SolveWorkbench.module.css";

type SolveNotePanelProps = {
  title: string;
  meta?: string;
  children: ReactNode;
};

export function SolveNotePanel({ title, meta, children }: SolveNotePanelProps) {
  return (
    <section className={styles.panel}>
      {title || meta ? (
        <div className={styles.panelHeader}>
          {title ? <h2>{title}</h2> : null}
          {meta ? <p>{meta}</p> : null}
        </div>
      ) : null}
      {children}
    </section>
  );
}
