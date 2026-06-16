import type {
  SolveDiagramPrimitive,
  SolveDiagramStep,
  SolveFormulaNoteItem,
  SolveResponse,
  SolveWorkspaceResponse,
  StructuredStep,
} from "./solveBackendTypes";
import type { Capabilities, HistoryItem } from "../../lib/types";
import {
  formatBackendState,
  formatItemCount,
  formatSelfCheckLabel,
  formatStepCount,
  formatTimeLabel,
  localizeDiagramMode,
  localizeQuestionType,
  localizeSkill,
  localizeSubject,
  workbenchCopy,
} from "./solveWorkbenchCopy";

export type SidebarSolveViewModel = {
  subjectLabel: string;
  questionTypeLabel: string;
  skillLabel: string;
};

export type CapabilityViewModel = {
  backendStatusLabel: string;
  subjects: Array<{ label: string; value: string }>;
};

export type HistoryItemViewModel = {
  id: string;
  solveId: string;
  question: string;
  preview: string;
  archiveTitle: string;
  timeLabel: string;
  subjectLabel: string;
  questionTypeLabel: string;
};

export type HistoryTypeGroupViewModel = {
  id: string;
  label: string;
  items: HistoryItemViewModel[];
};

export type HistorySubjectGroupViewModel = {
  id: string;
  label: string;
  typeGroups: HistoryTypeGroupViewModel[];
};

export type SidebarStatusRowViewModel = {
  id: string;
  label: string;
  value: string;
};

export type SidebarViewModel = {
  statusRows: SidebarStatusRowViewModel[];
  historyItems: HistoryItemViewModel[];
  historyGroups: HistorySubjectGroupViewModel[];
};

export type StepFormulaViewModel = {
  id: string;
  label: string;
  text: string;
  latex: string | null;
};

export type StepItemViewModel = {
  id: string;
  orderLabel: string;
  title: string;
  explanation: string;
  formulas: StepFormulaViewModel[];
  selfCheckLabel: string | null;
};

export type ProblemBlockViewModel = {
  id: string;
  type: "problem";
  title: string;
  text: string;
  subjectLabel: string;
  questionTypeLabel: string;
  generatedAtLabel: string;
};

export type StepsBlockViewModel = {
  id: string;
  type: "steps";
  title: string;
  meta: string;
  items: StepItemViewModel[];
};

export type DiagramBlockViewModel = {
  id: string;
  type: "diagram";
  title: string;
  meta: string;
  viewport: {
    width: number;
    height: number;
  };
  steps: SolveDiagramStep[];
  primitives: SolveDiagramPrimitive[];
  emptyMessage: string;
};

export type FormulasBlockItemViewModel = {
  id: string;
  stepTitle: string;
  label: string;
  text: string;
  latex: string | null;
};

export type FormulasBlockViewModel = {
  id: string;
  type: "formulas";
  title: string;
  meta: string;
  items: FormulasBlockItemViewModel[];
};

export type AnswerBlockViewModel = {
  id: string;
  type: "answer";
  title: string;
  text: string;
  answerJson: string;
};

export type ExplanationItemViewModel = {
  id: string;
  label: string;
  text: string;
};

export type ExplanationBlockViewModel = {
  id: string;
  type: "explanation";
  title: string;
  items: ExplanationItemViewModel[];
};

export type TextBlockViewModel = {
  id: string;
  type: "text";
  title: string;
  text: string;
};

export type NoteBlockViewModel =
  | ProblemBlockViewModel
  | StepsBlockViewModel
  | DiagramBlockViewModel
  | FormulasBlockViewModel
  | AnswerBlockViewModel
  | ExplanationBlockViewModel
  | TextBlockViewModel;

export type WorkbenchViewModel = {
  solveMeta: SidebarSolveViewModel;
  blocks: NoteBlockViewModel[];
  initialActiveStepId: string | null;
};

function toSidebarSolveViewModel(solve: SolveResponse): SidebarSolveViewModel {
  return {
    subjectLabel: localizeSubject(solve.subject),
    questionTypeLabel: localizeQuestionType(solve.question_type),
    skillLabel: localizeSkill(solve.skill),
  };
}

function formatGeneratedAtLabel(date = new Date()): string {
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function toCapabilityViewModel(capabilities: Capabilities | null): CapabilityViewModel {
  return {
    backendStatusLabel: formatBackendState(capabilities !== null),
    subjects:
      capabilities?.subjects.map((subject) => ({
        label: localizeSubject(subject.name),
        value: subject.name,
      })) ?? [],
  };
}

export function toHistoryItemViewModels(items: HistoryItem[]): HistoryItemViewModel[] {
  return items.map((item) => ({
    id: item.solve_id,
    solveId: item.solve_id,
    question: item.question_snippet,
    preview: item.question_snippet,
    archiveTitle: buildArchiveTitle(item.question_snippet),
    timeLabel: formatTimeLabel(item.created_at),
    subjectLabel: localizeSubject(item.subject),
    questionTypeLabel: localizeQuestionType(item.question_type),
  }));
}

function buildArchiveTitle(question: string): string {
  const normalized = question
    .replace(/\s+/g, " ")
    .replace(/[，。；;：:、]/g, " ")
    .trim();

  if (!normalized) {
    return "未命名题目";
  }

  const featureParts: string[] = [];
  const leading = normalized.match(/^(.{2,18}?(?:杆|梁|块|物体|小球|绳|弹簧|电路|矩阵|函数))/)?.[1];
  const ask = normalized.match(/(?:求|计算|判断|证明|解)(.{2,16})/)?.[0];

  if (leading) {
    featureParts.push(leading);
  }

  if (ask) {
    featureParts.push(ask);
  }

  if (featureParts.length > 0) {
    return `${featureParts[0]}......${featureParts.at(-1)}`;
  }

  return normalized.length > 22 ? `${normalized.slice(0, 18)}......` : normalized;
}

function toHistoryGroups(items: HistoryItemViewModel[]): HistorySubjectGroupViewModel[] {
  const subjectGroups = new Map<string, HistorySubjectGroupViewModel>();

  for (const item of items) {
    const subjectGroup =
      subjectGroups.get(item.subjectLabel) ??
      {
        id: item.subjectLabel,
        label: item.subjectLabel,
        typeGroups: [],
      };
    const typeGroup =
      subjectGroup.typeGroups.find((group) => group.label === item.questionTypeLabel) ??
      {
        id: `${item.subjectLabel}-${item.questionTypeLabel}`,
        label: item.questionTypeLabel,
        items: [],
      };

    if (!subjectGroups.has(item.subjectLabel)) {
      subjectGroups.set(item.subjectLabel, subjectGroup);
    }

    if (!subjectGroup.typeGroups.some((group) => group.id === typeGroup.id)) {
      subjectGroup.typeGroups.push(typeGroup);
    }

    typeGroup.items.push(item);
  }

  return Array.from(subjectGroups.values());
}

export function toSidebarViewModel(input: {
  capability: CapabilityViewModel | null;
  solveMeta: SidebarSolveViewModel | null;
  historyItems: HistoryItemViewModel[];
}): SidebarViewModel {
  return {
    historyGroups: toHistoryGroups(input.historyItems),
    statusRows: [
      {
        id: "backend",
        label: workbenchCopy.labels.backend,
        value: input.capability?.backendStatusLabel ?? workbenchCopy.backendState.offline,
      },
      {
        id: "subject",
        label: workbenchCopy.labels.subject,
        value: input.solveMeta?.subjectLabel ?? workbenchCopy.fallback.unknown,
      },
      {
        id: "question_type",
        label: workbenchCopy.labels.questionType,
        value: input.solveMeta?.questionTypeLabel ?? workbenchCopy.fallback.unknown,
      },
      {
        id: "skill",
        label: workbenchCopy.labels.skill,
        value: input.solveMeta?.skillLabel ?? workbenchCopy.fallback.unknown,
      },
    ],
    historyItems: input.historyItems,
  };
}

function toStepItemViewModel(step: StructuredStep): StepItemViewModel {
  return {
    id: step.id,
    orderLabel: `0${step.order}`.slice(-2),
    title: step.title,
    explanation: step.explanation,
    formulas: step.formulas.map((item) => ({
      id: item.id,
      label: item.label,
      text: item.text,
      latex: item.latex ?? null,
    })),
    selfCheckLabel: formatSelfCheckLabel(step.self_check_question),
  };
}

function toFormulaItemViewModel(item: SolveFormulaNoteItem): FormulasBlockItemViewModel {
  return {
    id: item.id,
    stepTitle: item.step_title,
    label: item.label,
    text: item.text,
    latex: item.latex ?? null,
  };
}

function toExplanationItems(explanation: SolveResponse["student_explanation"]): ExplanationItemViewModel[] {
  return [
    {
      id: "summary",
      label: workbenchCopy.explanation.summary,
      text: explanation?.summary ?? "",
    },
    {
      id: "intuition",
      label: workbenchCopy.explanation.intuition,
      text: explanation?.intuition ?? "",
    },
    {
      id: "common_mistake",
      label: workbenchCopy.explanation.commonMistake,
      text: explanation?.common_mistake ?? "",
    },
    {
      id: "self_check_question",
      label: workbenchCopy.explanation.selfCheck,
      text: explanation?.self_check_question ?? "",
    },
  ];
}

export function toWorkbenchViewModel(response: SolveWorkspaceResponse): WorkbenchViewModel {
  const solveMeta = toSidebarSolveViewModel(response.solve);

  return {
    solveMeta,
    initialActiveStepId: response.structured_steps[0]?.id ?? null,
    blocks: response.blocks.map((block): NoteBlockViewModel => {
      if (block.type === "problem") {
        return {
          id: block.id,
          type: "problem",
          title: block.title,
          text: block.text,
          subjectLabel: solveMeta.subjectLabel,
          questionTypeLabel: solveMeta.questionTypeLabel,
          generatedAtLabel: formatGeneratedAtLabel(),
        };
      }

      if (block.type === "steps") {
        return {
          id: block.id,
          type: "steps",
          title: block.title,
          meta: formatStepCount(block.items.length),
          items: block.items.map(toStepItemViewModel),
        };
      }

      if (block.type === "diagram") {
        return {
          id: block.id,
          type: "diagram",
          title: block.title,
          meta: localizeDiagramMode(block.mode),
          viewport: block.viewport,
          steps: block.steps,
          primitives: block.primitives,
          emptyMessage: workbenchCopy.messages.emptyDiagram,
        };
      }

      if (block.type === "formulas") {
        return {
          id: block.id,
          type: "formulas",
          title: block.title,
          meta: formatItemCount(block.items.length),
          items: block.items.map(toFormulaItemViewModel),
        };
      }

      if (block.type === "answer") {
        return {
          id: block.id,
          type: "answer",
          title: block.title,
          text: block.text,
          answerJson: JSON.stringify(block.raw_answer, null, 2),
        };
      }

      if (block.type === "explanation") {
        return {
          id: block.id,
          type: "explanation",
          title: block.title,
          items: toExplanationItems(block.explanation),
        };
      }

      return {
        id: block.id,
        type: "text",
        title: block.title,
        text: block.text,
      };
    }),
  };
}
