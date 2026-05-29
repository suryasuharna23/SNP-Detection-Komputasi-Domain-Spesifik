import type { PipelineResult, RunParams, SensitivityResult } from "./types";

const BASE = "/api";

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Request failed");
  }
  return res.json() as Promise<T>;
}

export function runPipeline(params: RunParams): Promise<PipelineResult> {
  return post("/run", params);
}

export function runSensitivity(params: {
  ref_length: number;
  max_snps: number;
  n_points: number;
  n_trials: number;
}): Promise<SensitivityResult> {
  return post("/sensitivity", params);
}
