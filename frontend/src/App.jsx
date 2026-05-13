import { Routes, Route, Link, Navigate } from "react-router-dom";
import Home from "./screens/Home.jsx";
import NewEpisode from "./screens/NewEpisode.jsx";
import ShotReview from "./screens/ShotReview.jsx";

export default function App() {
  return (
    <div className="app-shell">
      <header className="top">
        <h1>Story Engine</h1>
        <nav>
          <Link to="/">Home</Link>
          {" · "}
          <Link to="/new">New episode</Link>
        </nav>
      </header>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/new" element={<NewEpisode />} />
        <Route path="/review/:episodeId" element={<ShotReview />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}
