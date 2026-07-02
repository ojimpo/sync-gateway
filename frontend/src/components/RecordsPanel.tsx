import { useEffect, useState } from "react";
import { api, type Record, type Source } from "../api";
import { HoverRow, TableContainer, tableTdStyle, tableThStyle } from "./Table";

export default function RecordsPanel() {
  const [records, setRecords] = useState<Record[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [filter, setFilter] = useState("");

  useEffect(() => { api.sources().then(setSources); }, []);

  useEffect(() => {
    api.records({ source: filter || undefined, limit: 100 }).then(setRecords);
  }, [filter]);

  const sourceMap = Object.fromEntries(sources.map(s => [s.id, s]));

  const tdStyle: React.CSSProperties = { ...tableTdStyle, verticalAlign: "top", fontSize: 13 };
  const thStyle: React.CSSProperties = { ...tableThStyle, whiteSpace: "nowrap" };

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

      <TableContainer minWidth={800}>
          <thead>
            <tr style={{ background: "var(--surface2)" }}>
              {["ID", "Source", "Type", "Ext ID", "Title", "Status", "Event Date", "Ingested At", "Payload"].map(c => (
                <th key={c} style={thStyle}>{c}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {records.length === 0 ? (
              <tr><td colSpan={9} style={{ ...tdStyle, color: "var(--text-muted)", textAlign: "center", padding: 24 }}>No data</td></tr>
            ) : records.map(r => (
              <HoverRow key={r.id}>
                <td style={{ ...tdStyle, color: "var(--text-muted)", fontSize: 12 }}>{r.id}</td>
                <td style={tdStyle}>
                  <span style={{ fontFamily: "monospace", fontSize: 12, color: "var(--accent)" }}>
                    {sourceMap[r.source_id]?.slug ?? r.source_id}
                  </span>
                </td>
                <td style={tdStyle}>
                  <span style={{ color: "var(--text-muted)", fontSize: 12 }}>{r.record_type}</span>
                </td>
                <td style={tdStyle}>
                  <span style={{ fontFamily: "monospace", fontSize: 11, color: "var(--text-muted)" }}>
                    {r.external_id ?? "—"}
                  </span>
                </td>
                <td style={{ ...tdStyle, maxWidth: 180, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {r.title ?? "—"}
                </td>
                <td style={tdStyle}>{r.status ?? "—"}</td>
                <td style={{ ...tdStyle, whiteSpace: "nowrap", fontSize: 12 }}>
                  {r.event_date ? new Date(r.event_date).toLocaleDateString() : "—"}
                </td>
                <td style={{ ...tdStyle, whiteSpace: "nowrap", fontSize: 11, color: "var(--text-muted)" }}>
                  {new Date(r.ingested_at).toLocaleString()}
                </td>
                <td style={{ ...tdStyle, maxWidth: 260 }}>
                  <PayloadCell payload={r.payload} />
                </td>
              </HoverRow>
            ))}
          </tbody>
      </TableContainer>
    </>
  );
}

function PayloadCell({ payload }: { payload: unknown }) {
  const [open, setOpen] = useState(false);
  if (payload == null) return <span style={{ color: "var(--text-muted)" }}>—</span>;

  const compact = JSON.stringify(payload);
  const preview = compact.length > 60 ? compact.slice(0, 60) + "…" : compact;

  return (
    <div>
      <button
        onClick={() => setOpen(v => !v)}
        style={{
          background: "none", border: "none", padding: 0, cursor: "pointer",
          fontSize: 11, color: "var(--text-muted)", fontFamily: "monospace",
          textAlign: "left", display: "flex", alignItems: "baseline", gap: 4,
        }}
      >
        <span style={{ color: "var(--accent)", fontSize: 10 }}>{open ? "▼" : "▶"}</span>
        <span>{preview}</span>
      </button>
      {open && (
        <pre style={{
          marginTop: 8, fontSize: 10, color: "var(--text)", background: "var(--bg)",
          padding: "8px", borderRadius: 4, overflow: "auto", maxHeight: 200,
          whiteSpace: "pre-wrap", wordBreak: "break-all",
        }}>
          {JSON.stringify(payload, null, 2)}
        </pre>
      )}
    </div>
  );
}
