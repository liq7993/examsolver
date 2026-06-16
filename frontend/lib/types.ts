export type JsonObject = Record<string, unknown>;

export type Step = {
  index: number;
  description: string;
  formula_latex: string | null;
  image_hint: string | null;
};

export type Citation = {
  source: string;
  chunk_id: string;
  page: number | null;
  snippet: string;
};

export type FormulaCard = {
  title: string;
  formula_latex: string;
  explanation: string;
};

export type Flashcard = {
  front: string;
  back: string;
  tag: string;
};

export type StudentExplanation = {
  summary: string;
  intuition: string;
  step_by_step: string[];
  common_mistake: string;
  self_check_question: string;
};

export type NoteEntry = {
  solve_id: string;
  title: string;
  question_latex: string;
  steps: Step[];
  answer: string | JsonObject | null;
  student_explanation: StudentExplanation | null;
  common_mistakes: string[];
  related_formulas: FormulaCard[];
  flashcards: Flashcard[];
  citations: Citation[];
  subject: string | null;
  question_type: string;
  created_at: string | null;
};

export type SolveResponse = {
  success: boolean;
  solve_id: string;
  subject: string | null;
  question_type: string;
  skill: string;
  steps: string[];
  answer: string | JsonObject | null;
  message: string;
  student_explanation: StudentExplanation | null;
  citations: Citation[];
  fallback_reasons: string[];
  diagnostics: JsonObject;
  note: NoteEntry | null;
};

export type HistoryItem = {
  solve_id: string;
  subject: string | null;
  question_type: string;
  skill: string;
  success: boolean;
  created_at: string;
  question_snippet: string;
};

export type HistoryPage = {
  items: HistoryItem[];
  limit: number;
  offset: number;
  has_more: boolean;
  next_offset: number | null;
};

export type SubjectCapability = {
  name: string;
  question_types: string[];
};

export type SkillCapability = {
  name: string;
  version: string;
  subject: string;
  question_types: string[];
};

export type Capabilities = {
  subjects: SubjectCapability[];
  skills: SkillCapability[];
};
