import type { SolveHistorySummary } from "./solveBackendTypes";

export type WorkbenchBackendInfo = {
  connected: boolean;
  base_url: string | null;
  solver: string | null;
};

export type CapabilityResponse = {
  backend?: WorkbenchBackendInfo;
  additional_surfaces?: string[];
  error?: string;
};

export type HistoryResponse = {
  records: SolveHistorySummary[];
  has_more: boolean;
  error?: string;
};
