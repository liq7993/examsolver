export const homeCopy = {
  brandAriaLabel: "ExamSolver 标志",
  welcome: "欢迎使用，请点击右侧进入工作区。",
  apiLink: "API 配置",
  entryEyebrow: "工作区入口",
  entryTitle: "进入工作区",
  entryButton: "打开",
} as const;

export const workbenchCopy = {
  exampleQuestion: "一个 10 N 的力向右作用，求它的平衡力。",
  sections: {
    status: "状态",
    recentHistory: "最近记录",
  },
  labels: {
    backend: "后端",
    subject: "学科",
    questionType: "题型",
    skill: "技能",
  },
  fallback: {
    unknown: "未识别",
  },
  backendState: {
    connected: "已连接",
    offline: "离线",
  },
  header: {
    eyebrow: "解题笔记工作区",
    title: "按解题步骤组织笔记",
    placeholder: "输入当前支持的受力平衡题",
    submitIdle: "生成笔记",
    submitLoading: "求解中...",
    exampleButton: "示例题",
  },
  errors: {
    readHistoryFailed: "读取历史失败",
    readCapabilitiesFailed: "读取能力信息失败",
    emptyQuestion: "题目不能为空。",
    solveFailed: "笔记求解失败",
  },
  explanation: {
    summary: "总结",
    intuition: "直觉",
    commonMistake: "易错点",
    selfCheck: "自检",
  },
  messages: {
    emptyWorkspace: "输入题目开始生成解题笔记。",
    loadingWorkspace: "正在生成解题笔记...",
    emptyDiagram: "当前题目还没有可展示的 v0 图解。",
  },
  prefixes: {
    selfCheck: "自检：",
  },
} as const;

export function formatTimeLabel(value: string): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("zh-CN", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function localizeQuestionType(questionType: string): string {
  switch (questionType) {
    case "force_balance":
      return "受力平衡";
    case "rod_hinge_rope":
      return "杆-铰链-绳平衡";
    case "general_llm":
      return "静力学";
    case "unknown":
      return "未识别";
    default:
      return questionType;
  }
}

export function localizeSkill(skill: string): string {
  switch (skill) {
    case "force_balance":
      return "受力平衡求解";
    case "rod_hinge_rope":
      return "杆件静力学求解";
    case "unknown":
      return "兜底处理";
    default:
      return skill;
  }
}

export function localizeSubject(subject: string | null): string {
  switch (subject) {
    case "engineering_mechanics":
      return "工程力学";
    case "unknown":
    case null:
      return "未识别";
    default:
      return subject;
  }
}

export function localizeDiagramMode(mode: string): string {
  switch (mode) {
    case "find_balanced_force":
      return "平衡力";
    case "find_components":
      return "力分解";
    case "check_equilibrium":
      return "平衡判断";
    case "unsupported":
      return "暂不支持";
    default:
      return mode;
  }
}

export function formatStepCount(count: number): string {
  return `${count} 步`;
}

export function formatItemCount(count: number): string {
  return `${count} 项`;
}

export function formatSubmitLabel(isSubmitting: boolean): string {
  return isSubmitting ? workbenchCopy.header.submitLoading : workbenchCopy.header.submitIdle;
}

export function formatBackendState(connected: boolean): string {
  return connected ? workbenchCopy.backendState.connected : workbenchCopy.backendState.offline;
}

export function formatSelfCheckLabel(question: string | null | undefined): string | null {
  if (!question) {
    return null;
  }

  return `${workbenchCopy.prefixes.selfCheck}${question}`;
}
