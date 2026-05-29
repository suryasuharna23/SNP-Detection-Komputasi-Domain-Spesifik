import type { AIGuide, PipelineResult, RunParams, SensitivityResult } from "./types";

const BASE = (import.meta.env.VITE_API_BASE_URL ?? "/api").replace(/\/$/, "");

function errorMessage(detail: unknown, fallback: string): string {
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object" && "message" in detail) {
    const message = (detail as { message?: unknown }).message;
    if (typeof message === "string") return message;
  }
  return fallback;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorMessage(err.detail, res.statusText || "Request failed"));
  }
  return res.json() as Promise<T>;
}

export function runPipeline(params: RunParams): Promise<PipelineResult> {
  return post("/run", params);
}

export function generateAIGuide(result: PipelineResult): Promise<AIGuide> {
  return post("/ai/guide", { result });
}

export function runSensitivity(params: {
  ref_length: number;
  max_snps: number;
  n_points: number;
  n_trials: number;
}): Promise<SensitivityResult> {
  return post("/sensitivity", params);
}

export function generateClinicalReport(result: PipelineResult): Promise<{ report: string }> {
  return post("/clinical-report", { result });
}
