import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

const STATUS_LABEL = {
  draft:      { dot: "#9ca3af", text: "Draft" },
  scripted:   { dot: "#f59e0b", text: "Scripted" },
  approved:   { dot: "#3b82f6", text: "Approved" },
  generating: { dot: "#8b5cf6", text: "Generating…" },
  assembling: { dot: "#06b6d4", text: "Assembling" },
  done:       { dot: "#22c55e", text: "Done" },
};

function StatusBadge({ status }) {
  const s = STATUS_LABEL[status] || { dot: "#9ca3af", text: status };
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: "0.8rem", color: "#555" }}>
      <span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", background: s.dot }} />
      {s.text}
    </span>
  );
}

export default function Home() {
  const [episodes, setEpisodes] = useState([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    fetch("/api/episodes")
      .then((r) => r.json())
      .then((d) => setEpisodes(d.episodes || []))
      .catch(() => setErr("Could not reach the backend on port 5000."));
  }, []);

  const totalSpend = episodes.reduce((sum, ep) => sum + (ep.actual_cost_usd || 0), 0);

  return (
    <>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <div>
          <h2 style={{ margin: 0 }}>Episodes</h2>
          {episodes.length > 0 && (
            <p className="muted" style={{ margin: "4px 0 0" }}>
              {episodes.length} episode{episodes.length !== 1 ? "s" : ""}
              {totalSpend > 0 ? ` · $${totalSpend.toFixed(2)} spent` : ""}
            </p>
          )}
        </div>
        <Link to="/new">
          <button type="button" className="btn-primary">+ New episode</button>
        </Link>
      </div>

      {err && <p className="warn">{err}</p>}

      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        {episodes.length === 0 && !err && (
          <p className="muted" style={{ padding: "1.5rem", textAlign: "center" }}>
            No episodes yet — paste a story to create your first one.
          </p>
        )}
        <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
          {episodes.map((ep, i) => (
            <li
              key={ep.id}
              style={{
                padding: "0.85rem 1.25rem",
                borderBottom: i < episodes.length - 1 ? "1px solid #f0ede8" : "none",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                gap: "1rem",
              }}
            >
              <div style={{ minWidth: 0 }}>
                <Link
                  to={`/review/${encodeURIComponent(ep.id)}`}
                  style={{ fontWeight: 600, fontSize: "0.95rem", textDecoration: "none", color: "#1a1a2e" }}
                >
                  {ep.title || ep.id}
                </Link>
                <div style={{ marginTop: 3, display: "flex", gap: 10, flexWrap: "wrap" }}>
                  <StatusBadge status={ep.status} />
                  {ep.estimated_cost_usd != null && (
                    <span className="muted">est. ${Number(ep.estimated_cost_usd).toFixed(2)}</span>
                  )}
                </div>
              </div>
              <Link to={`/review/${encodeURIComponent(ep.id)}`} style={{ flexShrink: 0, color: "#2d6a4f", fontSize: "0.85rem" }}>
                Review →
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </>
  );
}
