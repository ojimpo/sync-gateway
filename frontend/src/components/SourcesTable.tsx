import { useEffect, useState } from "react";
import { api, type Source } from "../api";
import { Table } from "./Overview";

export default function SourcesTable() {
  const [sources, setSources] = useState<Source[]>([]);

  useEffect(() => { api.sources().then(setSources); }, []);

  return (
    <>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 24 }}>Sources</h1>
      <Table
        cols={["ID", "Slug", "Display Name", "Description", "Active", "Registered"]}
        rows={sources.map(s => [
          s.id,
          <code style={{ fontSize: 12, color: "var(--accent)", background: "var(--accent-soft)", padding: "1px 6px", borderRadius: 4 }}>{s.slug}</code>,
          s.display_name,
          s.description ?? <span style={{ color: "var(--text-muted)" }}>—</span>,
          s.active
            ? <span style={{ color: "var(--green)", fontWeight: 600 }}>active</span>
            : <span style={{ color: "var(--text-muted)" }}>inactive</span>,
          new Date(s.created_at).toLocaleDateString(),
        ])}
      />
    </>
  );
}
