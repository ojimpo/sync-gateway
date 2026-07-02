const BASE = import.meta.env.VITE_API_BASE ?? "";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`GET ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

export interface Source {
  id: number;
  slug: string;
  display_name: string;
  description: string | null;
  active: boolean;
  created_at: string;
  last_update_at: string | null;
  representative_url: string | null;
}

export interface Run {
  id: number;
  source_id: number;
  status: "running" | "success" | "failed";
  started_at: string;
  finished_at: string | null;
  records_processed: number;
  records_created: number;
  records_updated: number;
  records_failed: number;
  error_message: string | null;
}

export interface Record {
  id: number;
  source_id: number;
  run_id: number | null;
  external_id: string | null;
  record_type: string;
  title: string | null;
  author: string | null;
  rating: number | null;
  status: string | null;
  event_date: string | null;
  ingested_at: string;
  payload: unknown;
}

export const api = {
  sources: () => get<Source[]>("/api/v1/sources"),
  runs: (limit = 100) => get<Run[]>(`/api/v1/runs?limit=${limit}`),
  records: (params?: { source?: string; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.source) q.set("source", params.source);
    if (params?.limit) q.set("limit", String(params.limit));
    return get<Record[]>(`/api/v1/records?${q}`);
  },
  health: () => get<{ status: string }>("/healthz"),
};
