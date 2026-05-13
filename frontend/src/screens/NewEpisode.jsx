import { useState } from "react";
import { useNavigate } from "react-router-dom";

const HINTS = [
  "Once there was a small purple dragon who wanted to say hello…",
  "There was a girl who found a tiny door in the garden…",
  "A little cloud couldn't make rain and felt left out…",
];

export default function NewEpisode() {
  const [story, setStory] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const placeholder = HINTS[Math.floor(Math.random() * HINTS.length)];

  async function submit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await fetch("/api/episodes/new", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ story: story.trim() }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || res.statusText);
      navigate(`/review/${encodeURIComponent(data.episode.id)}`, { state: data });
    } catch (err) {
      setError(err.message || String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <h2 style={{ marginTop: 0 }}>New episode</h2>
      <p className="muted">
        Paste the story (spoken via Wispr Flow or typed). Claude will turn it into a shot list.
      </p>
      <form onSubmit={submit}>
        <textarea
          className="story-input"
          placeholder={placeholder}
          value={story}
          onChange={(e) => setStory(e.target.value)}
          disabled={loading}
        />
        {loading && (
          <p className="muted" style={{ marginTop: 8 }}>
            ✨ Reading the story and planning shots… (takes ~10 seconds)
          </p>
        )}
        <p style={{ marginTop: "0.75rem" }}>
          <button
            type="submit"
            className="btn-primary"
            disabled={loading || !story.trim()}
            style={{ fontSize: "1rem", padding: "0.65rem 1.4rem" }}
          >
            {loading ? "Planning…" : "✨ Turn into episode"}
          </button>
        </p>
      </form>
      {error && (
        <div className="amber" style={{ marginTop: "1rem" }}>
          <strong>Something went wrong</strong>
          <div className="muted" style={{ marginTop: 4 }}>{error}</div>
        </div>
      )}
    </>
  );
}
