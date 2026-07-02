import { useEffect, useState } from "react";
import { api, type Run, type Source } from "../api";
import { Table } from "./Table";

interface Stats {
  totalRuns: number;
  successRate: string;
  recordsIngested: number;
  activeSources: number;
}

function StatCard({ label, value, sub, color }: { label: string; value: string | number; sub?: string; color?: string }) {
  return (
    <div style={{
      background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)",
      padding: "20px 24px",
    }}>
      <div style={{ fontSize: 12, color: "var(--text-muted)", letterSpacing: "0.05em", textTransform: "uppercase", marginBottom: 8 }}>{label}</div>
      <div style={{ fontSize: 32, fontWeight: 700, color: color ?? "var(--text)", lineHeight: 1 }}>{value}</div>
      {sub && <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 6 }}>{sub}</div>}
    </div>
  );
}

export default function Overview() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [recentRuns, setRecentRuns] = useState<Run[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [health, setHealth] = useState<"ok" | "error" | "loading">("loading");

  useEffect(() => {
    Promise.all([api.runs(200), api.sources(), api.health()]).then(([runs, srcs, h]) => {
      const finished = runs.filter(r => r.status !== "running");
      const succeeded = runs.filter(r => r.status === "success");
      const total = runs.reduce((s, r) => s + r.records_processed, 0);
      setStats({
        totalRuns: runs.length,
        successRate: finished.length ? `${Math.round((succeeded.length / finished.length) * 100)}%` : "—",
        recordsIngested: total,
        activeSources: srcs.filter(s => s.active).length,
      });
      setRecentRuns(runs.slice(0, 8));
      setSources(srcs);
      setHealth(h.status === "ok" ? "ok" : "error");
    }).catch(() => setHealth("error"));
  }, []);

  const sourceMap = Object.fromEntries(sources.map(s => [s.id, s]));

  return (
    <>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 28 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700 }}>Overview</h1>
        <span style={{
          padding: "2px 10px", borderRadius: 99, fontSize: 11, fontWeight: 600,
          background: health === "ok" ? "rgba(34,197,94,0.15)" : health === "error" ? "rgba(239,68,68,0.15)" : "rgba(107,114,128,0.15)",
          color: health === "ok" ? "var(--green)" : health === "error" ? "var(--red)" : "var(--text-muted)",
        }}>
          {health === "ok" ? "● healthy" : health === "error" ? "● degraded" : "● checking"}
        </span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 16, marginBottom: 32 }}>
        <StatCard label="Total Runs" value={stats?.totalRuns ?? "—"} />
        <StatCard label="Success Rate" value={stats?.successRate ?? "—"} color="var(--green)" />
        <StatCard label="Records Ingested" value={stats?.recordsIngested?.toLocaleString() ?? "—"} />
        <StatCard label="Active Sources" value={stats?.activeSources ?? "—"} color="var(--accent)" />
      </div>

      <Section title="Recent Runs">
        <Table
          cols={["ID", "Source", "Status", "Records", "Duration"]}
          rows={recentRuns.map(r => [
            `#${r.id}`,
            sourceMap[r.source_id]?.display_name ?? r.source_id,
            <StatusBadge status={r.status} />,
            r.records_processed,
            r.finished_at ? dur(r.started_at, r.finished_at) : "running…",
          ])}
        />
      </Section>
    </>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 32 }}>
      <h2 style={{ fontSize: 14, fontWeight: 600, color: "var(--text-muted)", marginBottom: 12, textTransform: "uppercase", letterSpacing: "0.05em" }}>{title}</h2>
      {children}
    </div>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const cfg: Record<string, { bg: string; color: string }> = {
    success: { bg: "rgba(34,197,94,0.12)", color: "var(--green)" },
    failed: { bg: "rgba(239,68,68,0.12)", color: "var(--red)" },
    running: { bg: "rgba(59,130,246,0.12)", color: "var(--blue)" },
    pending: { bg: "rgba(107,114,128,0.12)", color: "var(--text-muted)" },
  };
  const c = cfg[status] ?? cfg.pending;
  return (
    <span style={{
      padding: "2px 8px", borderRadius: 99, fontSize: 11, fontWeight: 600,
      background: c.bg, color: c.color,
    }}>{status}</span>
  );
}

export function dur(start: string, end: string): string {
  const ms = new Date(end).getTime() - new Date(start).getTime();
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60000)}m ${Math.round((ms % 60000) / 1000)}s`;
}
