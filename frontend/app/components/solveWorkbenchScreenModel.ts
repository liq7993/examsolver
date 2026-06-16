import type { NoteBlockViewModel, SidebarViewModel } from "./solveWorkbenchViewModel";
import { workbenchCopy } from "./solveWorkbenchCopy";

export type WorkbenchScreenState = "loading" | "empty" | "solved" | "error";

export type WorkbenchScreenModel = {
  state: WorkbenchScreenState;
  sidebar: SidebarViewModel;
  blocks: NoteBlockViewModel[];
  activeStepId: string | null;
  bannerMessage: string | null;
  panelMessage: string | null;
  showBlocks: boolean;
};

export function toWorkbenchScreenModel(input: {
  sidebar: SidebarViewModel;
  blocks: NoteBlockViewModel[];
  activeStepId: string | null;
  error: string | null;
  isSubmitting: boolean;
  hasAttemptedSolve: boolean;
}): WorkbenchScreenModel {
  if (input.blocks.length > 0) {
    return {
      state: "solved",
      sidebar: input.sidebar,
      blocks: input.blocks,
      activeStepId: input.activeStepId,
      bannerMessage: input.error,
      panelMessage: null,
      showBlocks: true,
    };
  }

  if (input.error) {
    return {
      state: "error",
      sidebar: input.sidebar,
      blocks: [],
      activeStepId: input.activeStepId,
      bannerMessage: input.error,
      panelMessage: input.error,
      showBlocks: false,
    };
  }

  if (!input.hasAttemptedSolve || input.isSubmitting) {
    return {
      state: "loading",
      sidebar: input.sidebar,
      blocks: [],
      activeStepId: input.activeStepId,
      bannerMessage: null,
      panelMessage: workbenchCopy.messages.loadingWorkspace,
      showBlocks: false,
    };
  }

  return {
    state: "empty",
    sidebar: input.sidebar,
    blocks: [],
    activeStepId: input.activeStepId,
    bannerMessage: null,
    panelMessage: workbenchCopy.messages.emptyWorkspace,
    showBlocks: false,
  };
}
