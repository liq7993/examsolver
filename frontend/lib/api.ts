import type { Capabilities, HistoryPage, SolveResponse } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";
const BACKEND_UNAVAILABLE_MESSAGE = "后端未连接，请启动 uvicorn";

type HttpSolveResponse = Omit<
  SolveResponse,
  "citations" | "fallback_reasons" | "diagnostics" | "note"
> &
  Partial<Pick<SolveResponse, "citations" | "fallback_reasons" | "diagnostics" | "note">>;

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function solve(
  question: string,
  imagePaths: string[] = [],
  subject?: string,
): Promise<SolveResponse> {
  return normalizeSolveResponse(
    await requestJson<HttpSolveResponse>("/solve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        image_paths: imagePaths,
        subject: subject || undefined,
      }),
    }),
  );
}

export async function uploadSolveImage(file: File): Promise<string> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await requestJson<{ image_path: string }>("/solve/images", {
    method: "POST",
    body: formData,
  });
  return response.image_path;
}

export function getDocxExportUrl(solveId: string): string {
  return `${API_BASE}/export/docx/${encodeURIComponent(solveId)}`;
}

export async function getSolve(id: string): Promise<SolveResponse> {
  return normalizeSolveResponse(await requestJson<HttpSolveResponse>(`/solve/${encodeURIComponent(id)}`));
}

export async function getHistory(limit = 50, offset = 0): Promise<HistoryPage> {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  return requestJson<HistoryPage>(`/solve/history?${params.toString()}`);
}

export async function getCapabilities(): Promise<Capabilities> {
  return requestJson<Capabilities>("/solve/capabilities");
}

function normalizeSolveResponse(response: HttpSolveResponse): SolveResponse {
  return {
    ...response,
    student_explanation: response.student_explanation ?? null,
    citations: response.citations ?? [],
    fallback_reasons: response.fallback_reasons ?? [],
    diagnostics: response.diagnostics ?? {},
    note: response.note ?? null,
  };
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      cache: "no-store",
    });
  } catch {
    throw new ApiError(BACKEND_UNAVAILABLE_MESSAGE, undefined);
  }

  if (!response.ok) {
    throw new ApiError(await readErrorMessage(response), response.status);
  }

  return (await response.json()) as T;
}

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown; message?: unknown };
    const detail = payload.detail ?? payload.message;
    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
  } catch {
    // Fall through to the stable operator-facing error below.
  }

  return `${BACKEND_UNAVAILABLE_MESSAGE}（HTTP ${response.status}）`;
}
