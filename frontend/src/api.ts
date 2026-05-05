import type {
  CallSummary,
  CallDetail,
  CallAnalysis,
  HumanReview,
  Stats,
  ReviewPayload,
} from "./types";

const BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    // Do not include the response body in the error — it may contain PII from transcripts or call data.
    throw new Error(`Request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  getCalls(params?: { status?: "all" | "pending" | "reviewed" }): Promise<CallSummary[]> {
    const qs = params?.status && params.status !== "all" ? `?status=${params.status}` : "";
    return request(`/calls/${qs}`);
  },

  getStats(): Promise<Stats> {
    return request("/calls/stats/");
  },

  getCall(id: string): Promise<CallDetail> {
    return request(`/calls/${id}/`);
  },

  analyzeCall(id: string): Promise<CallAnalysis> {
    return request(`/calls/${id}/analyze/`, { method: "POST" });
  },

  submitReview(id: string, payload: ReviewPayload): Promise<HumanReview> {
    return request(`/calls/${id}/review/`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
};
