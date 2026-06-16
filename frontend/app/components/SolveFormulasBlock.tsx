import { renderFormulaHtml } from "./mathRendering";
import { SolveNotePanel } from "./SolveNotePanel";
import type { FormulasBlockViewModel } from "./solveWorkbenchViewModel";
import styles from "./SolveWorkbench.module.css";

type SolveFormulasBlockProps = {
  block: FormulasBlockViewModel;
};

export function SolveFormulasBlock({ block }: SolveFormulasBlockProps) {
  return (
    <SolveNotePanel title={block.title} meta={block.meta}>
      <div className={styles.formulaList}>
        {block.items.map((item) => {
          const rendered = renderFormulaHtml(item.latex ?? item.text, true);

          return (
            <div key={item.id} className={styles.formulaItem}>
              <span className={styles.stepHint}>{item.stepTitle}</span>
              <b>{item.label}</b>
              <div
                className={styles.formulaPreview}
                dangerouslySetInnerHTML={{ __html: rendered.html }}
              />
              {rendered.error ? <p className={styles.formulaError}>公式渲染失败：{rendered.error}</p> : null}
            </div>
          );
        })}
      </div>
    </SolveNotePanel>
  );
}
