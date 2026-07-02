import { useEffect, useState } from "react";
import { api, type Source } from "../api";
import { Table } from "./Overview";

function relativeTime(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const s = Math.floor(diffMs / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
}

export default function SourcesTable() {
  const [sources, setSources] = useState<Source[]>([]);

  useEffect(() => { api.sources().then(setSources); }, []);

  return (
    <>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 24 }}>Sources</h1>
      <Table
        cols={["ID", "Slug", "Display Name", "Description", "Active", "Registered", "Last Update", "URL"]}
        rows={sources.map(s => [
          s.id,
          <code style={{ fontSize: 12, color: "var(--accent)", background: "var(--accent-soft)", padding: "1px 6px", borderRadius: 4 }}>{s.slug}</code>,
          s.display_name,
          s.description ?? <span style={{ color: "var(--text-muted)" }}>—</span>,
          s.active
            ? <span style={{ color: "var(--green)", fontWeight: 600 }}>active</span>
            : <span style={{ color: "var(--text-muted)" }}>inactive</span>,
          new Date(s.created_at).toLocaleDateString(),
          s.last_update_at
            ? <span title={new Date(s.last_update_at).toLocaleString()}>{relativeTime(s.last_update_at)}</span>
            : <span style={{ color: "var(--text-muted)" }}>—</span>,
          s.representative_url
            ? <a href={s.representative_url} target="_blank" rel="noopener noreferrer" title={s.representative_url}
                style={{ color: "var(--accent)", textDecoration: "none", fontSize: 12 }}>
                {new URL(s.representative_url).hostname}
              </a>
            : <span style={{ color: "var(--text-muted)" }}>—</span>,
        ])}
      />
    </>
  );
}
