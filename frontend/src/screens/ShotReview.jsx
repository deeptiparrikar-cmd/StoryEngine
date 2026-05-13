import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";

function modelBadge(model) {
  const m = (model || "").toLowerCase();
  let cls = "badge ";
  if (m.includes("wan")) cls += "badge-wan";
  else if (m.includes("kling")) cls += "badge-kling";
  else if (m.includes("veo")) cls += "badge-veo";
  else cls += "badge-seed";
  return (
    <span className={cls} title={model}>
      {m || "?"}
    </span>
  );
}

export default function ShotReview() {
  const { episodeId } = useParams();
  const location = useLocation();
  const [data, setData] = useState(location.state || null);
  const [loading, setLoading] = useState(!location.state);
  const [error, setError] = useState("");

  useEffect(() => {
    if (location.state) {
      setData(location.state);
      setLoading(false);
      return;
    }
    if (!episodeId) return;
    setLoading(true);
    fetch(`/api/episodes/${encodeURIComponent(episodeId)}`)
      .then((r) => r.json())
      .then((d) => {
        if (!d.episode) throw new Error(d.error || "Not found");
        setData(d);
      })
      .catch((e) => setError(e.message || String(e)))
      .finally(() => setLoading(false));
  }, [episodeId, location.state]);

  if (loading) return <p className="muted">Loading…</p>;
  if (error) {
    return (
      <p className="warn">
        {error} — <Link to="/new">try New episode</Link>
      </p>
    );
  }
  if (!data) return <p className="muted">Nothing to show.</p>;

  const { episode, shots, plan, cost_estimate, max_spend_usd, over_budget } = data;
  const title = episode?.title || episodeId;
  const newChars = (plan?.characters_needed || []).filter((c) => c.is_new);

  return (
    <>
      <p>
        <Link to="/">← Home</Link>
      </p>
      <h2 style={{ marginTop: 0 }}>{title}</h2>
      {(episode?.episode_mood || episode?.palette) && (
        <p className="muted">
          {episode?.episode_mood}
          {episode?.palette ? ` · palette: ${episode.palette}` : ""}
        </p>
      )}
      {episode?.music_note && <p className="muted">{episode.music_note}</p>}

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Cost estimate</h3>
        {(cost_estimate?.lines || []).map((line) => (
          <div key={line.label} className="cost-line">
            <span>{line.label}</span>
            <span>${Number(line.usd).toFixed(2)}</span>
          </div>
        ))}
        <div className="cost-line cost-total">
          <span>Total</span>
          <span>${Number(cost_estimate?.total_usd || 0).toFixed(2)}</span>
        </div>
        {over_budget && (
          <p className="warn">
            Over your max spend (${Number(max_spend_usd).toFixed(2)}). You can still continue in a later sprint.
          </p>
        )}
      </div>

      {newChars.length > 0 && (
        <>
          <h3>New characters</h3>
          {newChars.map((c) => (
            <div key={c.name} className="amber">
              <strong>{c.name}</strong>
              <div className="muted" style={{ marginTop: "0.35rem" }}>
                {c.description}
              </div>
              <div className="muted" style={{ marginTop: "0.35rem" }}>
                Voice: (Sprint 2 — not wired yet)
              </div>
            </div>
          ))}
        </>
      )}

      <h3>Shots</h3>
      <div className="card">
        {(shots || []).map((s) => (
          <div key={s.id} className="shot-row">
            <div>
              <strong>{s.sequence}</strong>
            </div>
            <div>
              {modelBadge(s.model)}{" "}
              <span className="muted">
                {s.duration_sec}s
              </span>
              <div>{s.description}</div>
              {s.dialogue && (
                <div className="muted" style={{ marginTop: "0.25rem" }}>
                  “{s.dialogue}”
                </div>
              )}
              {s.emotional_tone && (
                <div className="muted" style={{ marginTop: "0.25rem" }}>
                  Tone: {s.emotional_tone}
                </div>
              )}
              {s.sound_design && (
                <div className="muted" style={{ marginTop: "0.25rem" }}>
                  Sound: {s.sound_design}
                </div>
              )}
            </div>
            <div className="muted" style={{ fontSize: "0.85rem" }}>
              <span title="Edit/remove in a later sprint">✎ ✕</span>
            </div>
          </div>
        ))}
      </div>

      <p>
        <button type="button" className="btn-primary" disabled title="Sprint 2 — generation not built yet">
          Generate episode — ${Number(cost_estimate?.total_usd || 0).toFixed(2)}
        </button>
      </p>
    </>
  );
}
