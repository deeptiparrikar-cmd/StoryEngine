import { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function NewEpisode() {
  const [story, setStory] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

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
      if (!res.ok) {
        throw new Error(data.error || res.statusText);
      }
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
      <form onSubmit={submit}>
        <textarea
          className="story-input"
          placeholder="Paste the story here…"
          value={story}
          onChange={(e) => setStory(e.target.value)}
          disabled={loading}
        />
        <p>
          <button type="submit" className="btn-primary" disabled={loading || !story.trim()}>
            {loading ? "Reading the story…" : "Turn into episode"}
          </button>
        </p>
      </form>
      {error && <p className="warn">{error}</p>}
    </>
  );
}
