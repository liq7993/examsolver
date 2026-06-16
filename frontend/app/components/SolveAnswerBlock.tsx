import { MathText } from "./MathText";
import { SolveNotePanel } from "./SolveNotePanel";
import type { AnswerBlockViewModel } from "./solveWorkbenchViewModel";

type SolveAnswerBlockProps = {
  block: AnswerBlockViewModel;
};

export function SolveAnswerBlock({ block }: SolveAnswerBlockProps) {
  return (
    <SolveNotePanel title={block.title}>
      <p>
        <MathText text={block.text} />
      </p>
    </SolveNotePanel>
  );
}
