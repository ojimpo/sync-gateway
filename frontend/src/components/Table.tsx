export const tableTdStyle: React.CSSProperties = { padding: "10px 14px", borderBottom: "1px solid var(--border)", color: "var(--text)", verticalAlign: "middle" };
export const tableThStyle: React.CSSProperties = { padding: "9px 14px", textAlign: "left", fontSize: 11, color: "var(--text-muted)", fontWeight: 600, letterSpacing: "0.05em", textTransform: "uppercase", borderBottom: "1px solid var(--border)" };

export function TableContainer({ minWidth, children }: { minWidth: number; children: React.ReactNode }) {
  return (
    <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", minWidth }}>
        {children}
      </table>
    </div>
  );
}

export function HoverRow({ children }: { children: React.ReactNode }) {
  return (
    <tr style={{ transition: "background 0.1s" }}
      onMouseEnter={e => (e.currentTarget.style.background = "var(--surface2)")}
      onMouseLeave={e => (e.currentTarget.style.background = "")}>
      {children}
    </tr>
  );
}

export function Table({ cols, rows }: { cols: string[]; rows: (React.ReactNode)[][] }) {
  return (
    <TableContainer minWidth={500}>
      <thead>
        <tr style={{ background: "var(--surface2)" }}>
          {cols.map(c => <th key={c} style={tableThStyle}>{c}</th>)}
        </tr>
      </thead>
      <tbody>
        {rows.length === 0
          ? <tr><td colSpan={cols.length} style={{ ...tableTdStyle, color: "var(--text-muted)", textAlign: "center", padding: 24 }}>No data</td></tr>
          : rows.map((row, i) => (
            <HoverRow key={i}>
              {row.map((cell, j) => <td key={j} style={tableTdStyle}>{cell}</td>)}
            </HoverRow>
          ))}
      </tbody>
    </TableContainer>
  );
}
