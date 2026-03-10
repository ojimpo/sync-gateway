import { useState } from "react";
import Overview from "./components/Overview";
import RunsTable from "./components/RunsTable";
import SourcesTable from "./components/SourcesTable";
import RecordsPanel from "./components/RecordsPanel";

type Page = "overview" | "runs" | "sources" | "records";

const NAV: { id: Page; label: string; icon: string }[] = [
  { id: "overview", label: "Overview", icon: "◈" },
  { id: "runs", label: "Runs", icon: "▶" },
  { id: "sources", label: "Sources", icon: "⬡" },
  { id: "records", label: "Records", icon: "≡" },
];

export default function App() {
  const [page, setPage] = useState<Page>("overview");

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden" }}>
      {/* Sidebar */}
      <aside style={{
        width: 220, background: "var(--surface)", borderRight: "1px solid var(--border)",
        display: "flex", flexDirection: "column", flexShrink: 0,
      }}>
        <div style={{ padding: "20px 16px 12px", borderBottom: "1px solid var(--border)" }}>
          <div style={{ fontSize: 15, fontWeight: 700, color: "var(--accent)", letterSpacing: "-0.3px" }}>
            arigato-gateway
          </div>
          <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>admin console</div>
        </div>
        <nav style={{ padding: "8px 8px", flex: 1 }}>
          {NAV.map(n => (
            <button key={n.id} onClick={() => setPage(n.id)} style={{
              display: "flex", alignItems: "center", gap: 10, width: "100%",
              padding: "9px 10px", borderRadius: "var(--radius)", border: "none",
              background: page === n.id ? "var(--accent-soft)" : "transparent",
              color: page === n.id ? "var(--accent)" : "var(--text-muted)",
              fontWeight: page === n.id ? 600 : 400, fontSize: 13,
              transition: "all 0.15s",
              cursor: "pointer",
            }}>
              <span style={{ fontSize: 16 }}>{n.icon}</span>
              {n.label}
            </button>
          ))}
        </nav>
        <div style={{ padding: "12px 16px", borderTop: "1px solid var(--border)", fontSize: 11, color: "var(--text-muted)" }}>
          <a href="/docs" target="_blank" style={{ color: "var(--text-muted)" }}>OpenAPI docs →</a>
        </div>
      </aside>

      {/* Main */}
      <main style={{ flex: 1, overflow: "auto", padding: "28px 32px" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto" }}>
          {page === "overview" && <Overview />}
          {page === "runs" && <RunsTable />}
          {page === "sources" && <SourcesTable />}
          {page === "records" && <RecordsPanel />}
        </div>
      </main>
    </div>
  );
}
