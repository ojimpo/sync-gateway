import { useEffect, useState } from "react";
import { api, type Record, type Source } from "../api";
import { Table } from "./Overview";

export default function RecordsPanel() {
  const [records, setRecords] = useState<Record[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [filter, setFilter] = useState("");

  useEffect(() => { api.sources().then(setSources); }, []);

  useEffect(() => {
    api.records({ source: filter || undefined, limit: 100 }).then(setRecords);
  }, [filter]);

  const sourceMap = Object.fromEntries(sources.map(s => [s.id, s]));

  return (
    <>
      <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700 }}>Records</h1>
        <select
          value={filter}
          onChange={e => setFilter(e.target.value)}
          style={{
            background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)",
            color: "var(--text)", padding: "6px 10px", fontSize: 13,
          }}
        >
          <option value="">All sources</option>
          {sources.map(s => <option key={s.slug} value={s.slug}>{s.display_name}</option>)}
        </select>
      </div>
      <Table
        cols={["ID", "Source", "Type", "Title", "Author", "Rating", "Status", "Event Date"]}
        rows={records.map(r => [
          r.id,
          sourceMap[r.source_id]?.slug ?? r.source_id,
          <span style={{ color: "var(--text-muted)", fontSize: 12 }}>{r.record_type}</span>,
          r.title ?? "—",
          r.author ?? "—",
          r.rating !== null ? (
            <span style={{ color: "var(--yellow)", fontWeight: 600 }}>★ {r.rating}</span>
          ) : "—",
          r.status ?? "—",
          r.event_date ? new Date(r.event_date).toLocaleDateString() : "—",
        ])}
      />
    </>
  );
}
