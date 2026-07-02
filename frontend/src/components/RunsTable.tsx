import { useEffect, useState } from "react";
import { api, type Run, type Source } from "../api";
import { StatusBadge, dur } from "./Overview";
import { Table } from "./Table";

export default function RunsTable() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [sources, setSources] = useState<Source[]>([]);

  useEffect(() => {
    Promise.all([api.runs(200), api.sources()]).then(([r, s]) => {
      setRuns(r);
      setSources(s);
    });
  }, []);

  const sourceMap = Object.fromEntries(sources.map(s => [s.id, s]));

  return (
    <>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 24 }}>Runs</h1>
      <Table
        cols={["ID", "Source", "Status", "Processed", "Created", "Updated", "Failed", "Duration", "Started"]}
        rows={runs.map(r => [
          `#${r.id}`,
          sourceMap[r.source_id]?.display_name ?? `src:${r.source_id}`,
          <StatusBadge status={r.status} />,
          r.records_processed,
          r.records_created,
          r.records_updated,
          r.records_failed > 0
            ? <span style={{ color: "var(--red)" }}>{r.records_failed}</span>
            : "0",
          r.finished_at ? dur(r.started_at, r.finished_at) : <span style={{ color: "var(--blue)" }}>running</span>,
          new Date(r.started_at).toLocaleString(),
        ])}
      />
    </>
  );
}
