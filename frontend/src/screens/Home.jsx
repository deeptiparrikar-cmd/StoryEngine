import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

export default function Home() {
  const [episodes, setEpisodes] = useState([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    fetch("/api/episodes")
      .then((r) => r.json())
      .then((d) => setEpisodes(d.episodes || []))
      .catch(() => setErr("Could not load episodes. Is the backend running on port 5000?"));
  }, []);

  return (
    <>
      <p className="muted">Sprint 1 — paste a story, review shots and cost (no generation yet).</p>
      <p>
        <Link to="/new">
          <button type="button" className="btn-primary">
            + New episode
          </button>
        </Link>
      </p>
      {err && <p className="warn">{err}</p>}
      <div className="card">
        <h2 style={{ marginTop: 0 }}>Episodes</h2>
        {episodes.length === 0 && !err && <p className="muted">No episodes yet.</p>}
        <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
          {episodes.map((ep) => (
            <li key={ep.id} style={{ padding: "0.5rem 0", borderBottom: "1px solid #eee" }}>
              <Link to={`/review/${encodeURIComponent(ep.id)}`}>
                <strong>{ep.title || ep.id}</strong>
              </Link>
              <span className="muted"> · {ep.status}</span>
              {ep.estimated_cost_usd != null && (
                <span className="muted"> · est. ${Number(ep.estimated_cost_usd).toFixed(2)}</span>
              )}
            </li>
          ))}
        </ul>
      </div>
    </>
  );
}
