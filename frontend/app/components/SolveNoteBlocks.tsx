import { SolveAnswerBlock } from "./SolveAnswerBlock";
import { SolveDiagramBlock } from "./SolveDiagramBlock";
import { SolveExplanationBlock } from "./SolveExplanationBlock";
import { SolveFormulasBlock } from "./SolveFormulasBlock";
import { SolveProblemBlock } from "./SolveProblemBlock";
import { SolveStepsBlock } from "./SolveStepsBlock";
import { SolveTextBlock } from "./SolveTextBlock";
import type { NoteBlockViewModel } from "./solveWorkbenchViewModel";
import styles from "./SolveWorkbench.module.css";

export function SolveNoteBlocks({
  blocks,
  activeStepId,
  setActiveStepId,
}: {
  blocks: NoteBlockViewModel[];
  activeStepId: string | null;
  setActiveStepId: (id: string) => void;
}) {
  return (
    <div className={styles.noteStack}>
      {blocks.map((block) => {
        if (block.type === "problem") {
          return <SolveProblemBlock key={block.id} block={block} />;
        }

        if (block.type === "steps") {
          return (
            <SolveStepsBlock
              key={block.id}
              block={block}
              activeStepId={activeStepId}
              setActiveStepId={setActiveStepId}
            />
          );
        }

        if (block.type === "diagram") {
          return <SolveDiagramBlock key={block.id} block={block} activeStepId={activeStepId} />;
        }

        if (block.type === "formulas") {
          return <SolveFormulasBlock key={block.id} block={block} />;
        }

        if (block.type === "answer") {
          return <SolveAnswerBlock key={block.id} block={block} />;
        }

        if (block.type === "explanation") {
          return <SolveExplanationBlock key={block.id} block={block} />;
        }

        return <SolveTextBlock key={block.id} block={block} />;
      })}
    </div>
  );
}
