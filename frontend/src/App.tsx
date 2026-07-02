import { useState, useEffect } from "react";
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
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(() => window.innerWidth <= 900);

  useEffect(() => {
    const handler = () => setIsMobile(window.innerWidth <= 900);
    window.addEventListener("resize", handler);
    return () => window.removeEventListener("resize", handler);
  }, []);

  const navigate = (p: Page) => {
    setPage(p);
    if (isMobile) setSidebarOpen(false);
  };

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden" }}>
      {/* Mobile backdrop */}
      {isMobile && sidebarOpen && (
        <div
          onClick={() => setSidebarOpen(false)}
          style={{
            position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)",
            zIndex: 199,
          }}
        />
      )}

      {/* Sidebar */}
      <aside style={{
        width: 220, background: "var(--surface)", borderRight: "1px solid var(--border)",
        display: "flex", flexDirection: "column", flexShrink: 0,
        ...(isMobile ? {
          position: "fixed",
          top: 0, bottom: 0, left: 0,
          zIndex: 200,
          transform: sidebarOpen ? "translateX(0)" : "translateX(-220px)",
          transition: "transform 0.2s ease",
        } : {}),
      }}>
        <div style={{
          padding: "20px 16px 12px", borderBottom: "1px solid var(--border)",
          display: "flex", justifyContent: "space-between", alignItems: "flex-start",
        }}>
          <div>
            <div style={{ fontSize: 15, fontWeight: 700, color: "var(--accent)", letterSpacing: "-0.3px" }}>
              sync-gateway
            </div>
            <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>admin console</div>
          </div>
          {isMobile && (
            <button
              onClick={() => setSidebarOpen(false)}
              style={{
                background: "none", border: "none", color: "var(--text-muted)",
                fontSize: 18, padding: "2px 4px", lineHeight: 1, cursor: "pointer",
              }}
            >✕</button>
          )}
        </div>
        <nav style={{ padding: "8px 8px", flex: 1 }}>
          {NAV.map(n => (
            <button key={n.id} onClick={() => navigate(n.id)} style={{
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
      <main style={{ flex: 1, overflow: "auto", padding: isMobile ? "16px" : "28px 32px" }}>
        {isMobile && (
          <button
            onClick={() => setSidebarOpen(true)}
            style={{
              display: "flex", alignItems: "center", justifyContent: "center",
              width: 36, height: 36,
              background: "var(--surface)", border: "1px solid var(--border)",
              borderRadius: "var(--radius)", color: "var(--text)", fontSize: 18,
              marginBottom: 16,
            }}
          >☰</button>
        )}
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
