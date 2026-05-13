import { useEffect, useRef, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Link, useLocation, useParams } from "react-router-dom";

const MODEL_BADGE = {
  wan:      { cls: "badge-wan",  label: "WAN" },
  kling:    { cls: "badge-kling", label: "KLING" },
  "veo-lite": { cls: "badge-veo", label: "VEO" },
};
function ModelBadge({ model }) {
  const m = (model || "").toLowerCase();
  const { cls, label } = MODEL_BADGE[m] || { cls: "badge-seed", label: (m || "?").toUpperCase() };
  return <span className={`badge ${cls}`}>{label}</span>;
}

const STATUS_COLOUR = {
  draft: "#9ca3af",
  scripted: "#f59e0b",
  approved: "#3b82f6",
  generating: "#8b5cf6",
  done: "#22c55e",
};
function StatusDot({ status }) {
  return (
    <span
      style={{
        display: "inline-block",
        width: 8,
        height: 8,
        borderRadius: "50%",
        background: STATUS_COLOUR[status] || "#9ca3af",
        marginRight: 6,
        verticalAlign: "middle",
      }}
    />
  );
}

/* ── Inline title edit ──────────────────────────────────── */
function EditableTitle({ episodeId, initial }) {
  const [title, setTitle] = useState(initial || "");
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const inputRef = useRef(null);

  useEffect(() => { if (editing) inputRef.current?.focus(); }, [editing]);

  async function save() {
    if (!title.trim()) { setEditing(false); return; }
    setSaving(true);
    try {
      await fetch(`/api/episodes/${encodeURIComponent(episodeId)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: title.trim() }),
      });
    } finally {
      setSaving(false);
      setEditing(false);
    }
  }

  if (editing) {
    return (
      <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <input
          ref={inputRef}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") save(); if (e.key === "Escape") setEditing(false); }}
          style={{ fontSize: "1.3rem", fontWeight: 700, border: "1px solid #2d6a4f", borderRadius: 6, padding: "0.2rem 0.5rem", width: "100%" }}
          disabled={saving}
        />
        <button className="btn-primary" onClick={save} disabled={saving} style={{ padding: "0.3rem 0.75rem" }}>
          {saving ? "…" : "Save"}
        </button>
        <button onClick={() => setEditing(false)} style={{ background: "none", border: "none", color: "#666", padding: "0.3rem" }}>✕</button>
      </span>
    );
  }

  return (
    <h2 style={{ marginTop: 0, display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
      {title}
      <button
        onClick={() => setEditing(true)}
        style={{ background: "none", border: "1px solid #ddd", borderRadius: 6, padding: "0.15rem 0.5rem", fontSize: "0.8rem", color: "#666", cursor: "pointer" }}
        title="Edit title"
      >
        ✎ edit
      </button>
    </h2>
  );
}

/* ── Shot card with inline edit ─────────────────────────── */
const MODELS = ["wan", "seedance", "kling", "veo-lite"];
const DURATIONS = [5, 6, 8, 10];

function ShotCard({ shot, onUpdate, onRemove }) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({
    description: shot.description || "",
    model: shot.model || "wan",
    duration_sec: shot.duration_sec || 6,
    dialogue: shot.dialogue || "",
  });
  const [saving, setSaving] = useState(false);
  const [removing, setRemoving] = useState(false);

  function field(k) {
    return (e) => setForm((f) => ({ ...f, [k]: e.target.value }));
  }

  async function save() {
    setSaving(true);
    try {
      const body = {
        description: form.description.trim(),
        model: form.model,
        duration_sec: parseInt(form.duration_sec),
        dialogue: form.dialogue.trim() || null,
      };
      await fetch(`/api/shots/${encodeURIComponent(shot.id)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      onUpdate({ ...shot, ...body });
      setEditing(false);
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    if (!window.confirm(`Remove shot ${shot.sequence}?`)) return;
    setRemoving(true);
    try {
      await fetch(`/api/shots/${encodeURIComponent(shot.id)}`, { method: "DELETE" });
      onRemove(shot.id);
    } finally {
      setRemoving(false);
    }
  }

  if (editing) {
    return (
      <div className="shot-row" style={{ background: "#fafffe", borderRadius: 8, padding: "0.75rem", marginBottom: "0.5rem", border: "1px solid #d1fae5" }}>
        <div style={{ fontWeight: 700, color: "#2d6a4f", minWidth: 24 }}>{shot.sequence}</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <textarea
            value={form.description}
            onChange={field("description")}
            rows={2}
            style={{ width: "100%", padding: "0.4rem", borderRadius: 6, border: "1px solid #ccc", font: "inherit" }}
          />
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <select value={form.model} onChange={field("model")} style={{ padding: "0.3rem", borderRadius: 6, border: "1px solid #ccc" }}>
              {MODELS.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
            <select value={form.duration_sec} onChange={field("duration_sec")} style={{ padding: "0.3rem", borderRadius: 6, border: "1px solid #ccc" }}>
              {DURATIONS.map((d) => <option key={d} value={d}>{d}s</option>)}
            </select>
            <input
              value={form.dialogue}
              onChange={field("dialogue")}
              placeholder="Dialogue (optional)"
              style={{ flex: 1, padding: "0.3rem", borderRadius: 6, border: "1px solid #ccc" }}
            />
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn-primary" onClick={save} disabled={saving} style={{ padding: "0.3rem 0.75rem" }}>
              {saving ? "Saving…" : "Save"}
            </button>
            <button onClick={() => setEditing(false)} style={{ background: "none", border: "1px solid #ccc", borderRadius: 6, padding: "0.3rem 0.75rem", cursor: "pointer" }}>
              Cancel
            </button>
          </div>
        </div>
        <div />
      </div>
    );
  }

  return (
    <div className="shot-row">
      <div style={{ fontWeight: 700, color: "#2d6a4f", paddingTop: 2 }}>{shot.sequence}</div>
      <div>
        <span style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap", marginBottom: 4 }}>
          <ModelBadge model={shot.model} />
          <span className="muted">{shot.duration_sec}s</span>
        </span>
        <div>{shot.description}</div>
        {shot.dialogue && (
          <div className="muted" style={{ marginTop: 4 }}>"{shot.dialogue}"</div>
        )}
        {shot.emotional_tone && (
          <div className="muted" style={{ marginTop: 4 }}>Tone: {shot.emotional_tone}</div>
        )}
        {shot.sound_design && (
          <div className="muted" style={{ marginTop: 4 }}>Sound: {shot.sound_design}</div>
        )}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 4, paddingTop: 2 }}>
        <button
          onClick={() => setEditing(true)}
          style={{ background: "none", border: "1px solid #ddd", borderRadius: 6, padding: "0.15rem 0.5rem", cursor: "pointer", fontSize: "0.8rem" }}
          title="Edit this shot"
        >
          ✎
        </button>
        <button
          onClick={remove}
          disabled={removing}
          style={{ background: "none", border: "1px solid #fca5a5", borderRadius: 6, padding: "0.15rem 0.5rem", cursor: "pointer", fontSize: "0.8rem", color: "#ef4444" }}
          title="Remove this shot"
        >
          ✕
        </button>
      </div>
    </div>
  );
}

/* ── Generation status banner ───────────────────────────── */
function GeneratingBanner({ episodeId, onDone }) {
  const [status, setStatus] = useState("approved");
  const timerRef = useRef(null);

  useEffect(() => {
    function poll() {
      fetch(`/api/episodes/${encodeURIComponent(episodeId)}/generate-status`)
        .then((r) => r.json())
        .then((d) => {
          const s = d.status || "generating";
          setStatus(s);
          if (s === "generating" || s === "approved") {
            timerRef.current = setTimeout(poll, 5000);
          } else {
            onDone(s);
          }
        })
        .catch(() => {
          timerRef.current = setTimeout(poll, 8000);
        });
    }
    timerRef.current = setTimeout(poll, 3000);
    return () => clearTimeout(timerRef.current);
  }, [episodeId, onDone]);

  return (
    <div style={{ background: "#f0fdf4", border: "1px solid #86efac", borderRadius: 10, padding: "1.25rem", marginTop: "1rem" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <span style={{ fontSize: "1.4rem" }}>
          {status === "generating" || status === "approved" ? "⏳" : status === "scripted" ? "✅" : "⚠️"}
        </span>
        <div>
          <strong>
            {status === "approved" ? "Starting generation…" :
             status === "generating" ? "Generating character images…" :
             status === "scripted" ? "Character images done!" : `Status: ${status}`}
          </strong>
          {(status === "generating" || status === "approved") && (
            <p className="muted" style={{ margin: "4px 0 0" }}>
              Creating 6 reference angles per new character via OpenRouter. Checking every 5s…
            </p>
          )}
          {status === "scripted" && (
            <p className="muted" style={{ margin: "4px 0 0" }}>
              Check <code>OUTPUT_DIR/characters/</code> for downloaded images.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

/* ── Main screen ────────────────────────────────────────── */
export default function ShotReview() {
  const { episodeId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const [data, setData] = useState(location.state || null);
  const [shots, setShots] = useState(null);
  const [loading, setLoading] = useState(!location.state);
  const [error, setError] = useState("");
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState("");

  useEffect(() => {
    const src = location.state;
    if (src) {
      setData(src);
      setShots(src.shots || src.shot_list || []);
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
        setShots(d.shots || d.shot_list || []);
      })
      .catch((e) => setError(e.message || String(e)))
      .finally(() => setLoading(false));
  }, [episodeId, location.state]);

  function handleUpdate(updated) {
    setShots((prev) => prev.map((s) => (s.id === updated.id ? updated : s)));
  }
  function handleRemove(id) {
    setShots((prev) => prev.filter((s) => s.id !== id));
  }

  async function handleGenerate() {
    setGenError("");
    setGenerating(true);
    try {
      const res = await fetch(`/api/episodes/${encodeURIComponent(episode.id)}/generate`, {
        method: "POST",
      });
      if (!res.ok) {
        const d = await res.json();
        throw new Error(d.error || res.statusText);
      }
    } catch (err) {
      setGenError(err.message || String(err));
      setGenerating(false);
    }
  }

  const handleGenDone = useCallback((finalStatus) => {
    setGenerating(false);
    if (finalStatus === "scripted") {
      // Refresh episode data to reflect updated status
      navigate(0);
    }
  }, [navigate]);

  if (loading) return <p className="muted" style={{ padding: "2rem" }}>Reading the story…</p>;
  if (error) return <p className="warn" style={{ padding: "2rem" }}>{error} — <Link to="/new">try again</Link></p>;
  if (!data) return <p className="muted">Nothing to show.</p>;

  const { episode, plan, cost_estimate, max_spend_usd, over_budget } = data;
  const displayShots = shots || [];
  const newChars = (plan?.characters_needed || []).filter((c) => c.is_new);
  const totalUsd = Number(cost_estimate?.total_usd || 0);

  return (
    <>
      <p><Link to="/">← Home</Link></p>

      <EditableTitle episodeId={episode?.id} initial={episode?.title || episodeId} />

      {(episode?.episode_mood || episode?.palette) && (
        <p className="muted">{episode.episode_mood}{episode.palette ? ` · ${episode.palette}` : ""}</p>
      )}
      {episode?.music_note && <p className="muted">{episode.music_note}</p>}

      {/* Cost estimate card */}
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
          <span>${totalUsd.toFixed(2)}</span>
        </div>
        {over_budget && (
          <p className="warn" style={{ marginBottom: 0 }}>
            Over your max spend (${Number(max_spend_usd).toFixed(2)}) — you can still proceed.
          </p>
        )}
      </div>

      {/* New characters */}
      {newChars.length > 0 && (
        <>
          <h3>New characters</h3>
          {newChars.map((c) => (
            <div key={c.name} className="amber">
              <strong>{c.name}</strong>
              <div className="muted" style={{ marginTop: 4 }}>{c.description}</div>
              <div className="muted" style={{ marginTop: 6, fontSize: "0.85rem" }}>
                Voice: assigned in Sprint 7 (ElevenLabs)
              </div>
            </div>
          ))}
        </>
      )}

      {/* Shot list */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <h3 style={{ marginBottom: 8 }}>Shots ({displayShots.length})</h3>
      </div>
      <div className="card" style={{ padding: "0.5rem 1rem" }}>
        {displayShots.length === 0 && (
          <p className="muted">No shots. Go back and paste a story to create new ones.</p>
        )}
        {displayShots.map((s) => (
          <ShotCard key={s.id} shot={s} onUpdate={handleUpdate} onRemove={handleRemove} />
        ))}
      </div>

      {/* Generation status banner */}
      {generating && <GeneratingBanner episodeId={episode?.id} onDone={handleGenDone} />}
      {genError && <p className="warn" style={{ marginTop: "0.75rem" }}>{genError}</p>}

      {/* Generate button */}
      {!generating && (
        <p style={{ marginTop: "1.25rem" }}>
          <button
            type="button"
            className="btn-primary"
            onClick={handleGenerate}
            disabled={displayShots.length === 0}
            style={{
              fontSize: "1rem",
              padding: "0.7rem 1.5rem",
              background: over_budget ? "#b45309" : undefined,
            }}
          >
            {over_budget ? "⚠ " : ""}Generate episode — ~${totalUsd.toFixed(2)}
          </button>
        </p>
      )}
    </>
  );
}
