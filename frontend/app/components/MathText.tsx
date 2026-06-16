import { renderFormulaHtml, renderLooseMathTextHtml } from "./mathRendering";
import styles from "./SolveWorkbench.module.css";

type MathTextProps = {
  text: string;
  display?: boolean;
};

export function MathText({ text, display = false }: MathTextProps) {
  const rendered = display ? renderFormulaHtml(text, true) : renderLooseMathTextHtml(text);

  return (
    <span
      className={display ? styles.mathTextBlock : styles.mathTextInline}
      dangerouslySetInnerHTML={{ __html: rendered.html }}
    />
  );
}
