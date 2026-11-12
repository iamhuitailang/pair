const BASE = "/api";

export interface SessionSummary {
  session_id: string;
  status: string;
  has_anomalies: boolean;
  anomaly_count: number;
  event_count: number;
  players: string[];
  started_at: string | null;
  duration_seconds: number;
  winner_player_id: string | null;
  completeness: number;
}

export interface SessionListResp {
  total: number;
  page: number;
  page_size: number;
  items: SessionSummary[];
}

export interface Filters {
  date_from?: string;
  date_to?: string;
  player_id?: string;
  status?: string;
}

function qs(params: Record<string, string | number | undefined>): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "") q.set(k, String(v));
  }
  const s = q.toString();
  return s ? `?${s}` : "";
}

export async function fetchSessions(f: Filters, page: number, pageSize: number): Promise<SessionListResp> {
  const r = await fetch(`${BASE}/sessions${qs({ ...f, page, page_size: pageSize })}`);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export async function fetchSessionDetail(id: string): Promise<any> {
  const r = await fetch(`${BASE}/sessions/${encodeURIComponent(id)}`);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export function exportUrl(f: Filters, format: "csv" | "json"): string {
  return `${BASE}/sessions/export${qs({ ...f, format })}`;
}
