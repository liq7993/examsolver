export type SolveFormula = {
  id: string;
  label: string;
  text: string;
  latex?: string | null;
};

export type StructuredStep = {
  id: string;
  order: number;
  title: string;
  explanation: string;
  formulas: SolveFormula[];
  self_check_question?: string | null;
};

export type StudentExplanation = {
  summary?: string | null;
  intuition?: string | null;
  common_mistake?: string | null;
  self_check_question?: string | null;
};

export type SolveResponse = {
  success: boolean;
  message?: string | null;
  subject: string | null;
  question_type: string;
  skill: string;
  student_explanation?: StudentExplanation | null;
};

export type SolveHistorySummary = {
  created_at: string;
  request: {
    question_preview: string;
  };
  response: {
    subject: string | null;
    question_type: string;
  };
};

export type SolveDiagramStep = {
  id: string;
  primitive_ids: string[];
};

export type SolveDiagramPrimitive =
  | {
      id: string;
      kind: "body";
      x: number;
      y: number;
      width: number;
      height: number;
    }
  | {
      id: string;
      kind: "highlight_box";
      x: number;
      y: number;
      width: number;
      height: number;
      tone: "result" | "default";
    }
  | {
      id: string;
      kind: "axis";
      origin: { x: number; y: number };
      x_length: number;
      y_length: number;
    }
  | {
      id: string;
      kind: "force_arrow";
      role: "given" | "balancing" | "component_x" | "component_y" | "resultant";
      from: { x: number; y: number };
      to: { x: number; y: number };
      label: string;
    }
  | {
      id: string;
      kind: "label";
      position: { x: number; y: number };
      text: string;
      tone: "default" | "muted" | "accent";
    }
  | {
      id: string;
      kind: "angle_marker";
      center: { x: number; y: number };
      radius: number;
      start_deg: number;
      end_deg: number;
    };

export type SolveFormulaNoteItem = {
  id: string;
  step_title: string;
  label: string;
  text: string;
  latex?: string | null;
};

export type NoteBlock =
  | {
      id: string;
      type: "problem";
      title: string;
      text: string;
    }
  | {
      id: string;
      type: "steps";
      title: string;
      items: StructuredStep[];
    }
  | {
      id: string;
      type: "diagram";
      title: string;
      mode: string;
      viewport: { width: number; height: number };
      steps: SolveDiagramStep[];
      primitives: SolveDiagramPrimitive[];
    }
  | {
      id: string;
      type: "formulas";
      title: string;
      items: SolveFormulaNoteItem[];
    }
  | {
      id: string;
      type: "answer";
      title: string;
      text: string;
      raw_answer: unknown;
    }
  | {
      id: string;
      type: "explanation";
      title: string;
      explanation?: StudentExplanation | null;
    }
  | {
      id: string;
      type: "text";
      title: string;
      text: string;
    };

export type SolveWorkspaceResponse = {
  solve: SolveResponse;
  warnings: string[];
  structured_steps: StructuredStep[];
  blocks: NoteBlock[];
};
