"""SQLite persistence for Story Engine (v3 + cinematic addendum schema)."""

from __future__ import annotations

import json
import re
import sqlite3
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "story_engine.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS episodes (
    id                   TEXT PRIMARY KEY,
    title                TEXT,
    raw_story            TEXT,
    status               TEXT DEFAULT 'draft',
    estimated_cost_usd   REAL,
    actual_cost_usd      REAL DEFAULT 0.0,
    created_at           INTEGER,
    episode_mood         TEXT,
    palette              TEXT,
    music_note           TEXT,
    plan_json            TEXT
);

CREATE TABLE IF NOT EXISTS shots (
    id                   TEXT PRIMARY KEY,
    episode_id           TEXT NOT NULL,
    sequence             INTEGER NOT NULL,
    description          TEXT,
    image_prompt         TEXT,
    video_prompt         TEXT,
    model                TEXT,
    duration_sec         INTEGER,
    dialogue             TEXT,
    characters_used      TEXT,
    emotional_tone       TEXT,
    cinematic_reference  TEXT,
    motion_intent        TEXT,
    sound_design         TEXT,
    transition_to_next   TEXT,
    image_status         TEXT DEFAULT 'pending',
    image_url            TEXT,
    image_local_path     TEXT,
    video_job_id         TEXT,
    video_status         TEXT DEFAULT 'pending',
    video_local_path     TEXT,
    voice_status         TEXT DEFAULT 'pending',
    voice_local_path     TEXT,
    retry_count          INTEGER DEFAULT 0,
    error_msg            TEXT,
    FOREIGN KEY (episode_id) REFERENCES episodes(id)
);

CREATE TABLE IF NOT EXISTS characters (
    id               TEXT PRIMARY KEY,
    name             TEXT NOT NULL,
    description      TEXT,
    voice_speaker    TEXT,
    ref_images       TEXT,
    episode_count    INTEGER DEFAULT 0,
    created_at       INTEGER
);

CREATE TABLE IF NOT EXISTS narration (
    id             TEXT PRIMARY KEY,
    episode_id     TEXT NOT NULL,
    position       TEXT NOT NULL,
    script         TEXT,
    voice_status   TEXT DEFAULT 'pending',
    local_path     TEXT,
    FOREIGN KEY (episode_id) REFERENCES episodes(id)
);

CREATE TABLE IF NOT EXISTS dubs (
    id             TEXT PRIMARY KEY,
    episode_id     TEXT NOT NULL,
    language_code  TEXT NOT NULL,
    status         TEXT DEFAULT 'pending',
    local_path     TEXT,
    error_msg      TEXT,
    FOREIGN KEY (episode_id) REFERENCES episodes(id)
);

CREATE TABLE IF NOT EXISTS cost_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_id   TEXT,
    service      TEXT,
    amount_usd   REAL,
    logged_at    INTEGER
);
"""


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_db()
    try:
        conn.executescript(SCHEMA)
        cur = conn.execute("PRAGMA table_info(episodes)")
        cols = {row[1] for row in cur.fetchall()}
        if cols and "plan_json" not in cols:
            conn.execute("ALTER TABLE episodes ADD COLUMN plan_json TEXT")
        conn.commit()
    finally:
        conn.close()


def _row_to_dict(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return dict(row)


def get_episode(episode_id: str) -> dict | None:
    conn = get_db()
    try:
        cur = conn.execute("SELECT * FROM episodes WHERE id = ?", (episode_id,))
        return _row_to_dict(cur.fetchone())
    finally:
        conn.close()


def create_episode(episode_id: str, title: str, raw_story: str) -> dict:
    now = int(time.time())
    conn = get_db()
    try:
        conn.execute(
            """
            INSERT INTO episodes (id, title, raw_story, status, created_at)
            VALUES (?, ?, ?, 'draft', ?)
            """,
            (episode_id, title or "", raw_story, now),
        )
        conn.commit()
        return get_episode(episode_id) or {}
    finally:
        conn.close()


def update_episode_status(episode_id: str, status: str) -> None:
    conn = get_db()
    try:
        conn.execute(
            "UPDATE episodes SET status = ? WHERE id = ?",
            (status, episode_id),
        )
        conn.commit()
    finally:
        conn.close()


def _slugify(text: str) -> str:
    s = (text or "").lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "character"


def update_episode_scripted(
    episode_id: str,
    *,
    title: str,
    episode_mood: str | None,
    palette: str | None,
    music_note: str | None,
    estimated_cost_usd: float,
) -> None:
    conn = get_db()
    try:
        conn.execute(
            """
            UPDATE episodes SET
                title = ?,
                episode_mood = ?,
                palette = ?,
                music_note = ?,
                estimated_cost_usd = ?,
                status = 'scripted'
            WHERE id = ?
            """,
            (title, episode_mood, palette, music_note, estimated_cost_usd, episode_id),
        )
        conn.commit()
    finally:
        conn.close()


def save_scripted_episode(
    episode_id: str,
    plan: dict,
    cost_estimate: dict,
) -> None:
    """Replace shots/narration for episode and upsert new characters (single transaction)."""
    conn = get_db()
    try:
        title = plan.get("episode_title") or "Untitled"
        estimated_cost_usd = float(cost_estimate["total_usd"])
        plan_snapshot = json.dumps(
            {
                "characters_needed": plan.get("characters_needed"),
                "narrator_intro": plan.get("narrator_intro"),
                "narrator_outro": plan.get("narrator_outro"),
                "cost_estimate": cost_estimate,
            },
            ensure_ascii=False,
        )
        conn.execute(
            """
            UPDATE episodes SET
                title = ?,
                episode_mood = ?,
                palette = ?,
                music_note = ?,
                estimated_cost_usd = ?,
                plan_json = ?,
                status = 'scripted'
            WHERE id = ?
            """,
            (
                title,
                plan.get("episode_mood"),
                plan.get("palette"),
                plan.get("music_note"),
                estimated_cost_usd,
                plan_snapshot,
                episode_id,
            ),
        )
        conn.execute("DELETE FROM shots WHERE episode_id = ?", (episode_id,))
        conn.execute("DELETE FROM narration WHERE episode_id = ?", (episode_id,))

        for shot in plan.get("shots") or []:
            sid = f"{episode_id}-s{int(shot['sequence']):03d}"
            characters_used = shot.get("characters_used") or []
            if isinstance(characters_used, list):
                characters_used = json.dumps(characters_used)
            conn.execute(
                """
                INSERT INTO shots (
                    id, episode_id, sequence, description,
                    image_prompt, video_prompt, model, duration_sec,
                    dialogue, characters_used,
                    emotional_tone, cinematic_reference, motion_intent,
                    sound_design, transition_to_next
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sid,
                    episode_id,
                    int(shot["sequence"]),
                    shot.get("description"),
                    shot.get("image_prompt"),
                    shot.get("video_prompt"),
                    shot.get("model"),
                    int(shot.get("duration_sec") or 6),
                    shot.get("dialogue"),
                    characters_used,
                    shot.get("emotional_tone"),
                    shot.get("cinematic_reference"),
                    shot.get("motion_intent"),
                    shot.get("sound_design"),
                    shot.get("transition_to_next"),
                ),
            )

        intro = plan.get("narrator_intro") or ""
        outro = plan.get("narrator_outro") or ""
        for position, script in (("intro", intro), ("outro", outro)):
            nid = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO narration (id, episode_id, position, script, voice_status)
                VALUES (?, ?, ?, ?, 'pending')
                """,
                (nid, episode_id, position, script),
            )

        for ch in plan.get("characters_needed") or []:
            if not ch.get("is_new"):
                continue
            name = (ch.get("name") or "").strip()
            if not name:
                continue
            cid = _slugify(name)
            desc = ch.get("description")
            conn.execute(
                """
                INSERT INTO characters (id, name, description, voice_speaker, ref_images, created_at)
                VALUES (?, ?, ?, NULL, '{}', ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    description = COALESCE(excluded.description, characters.description)
                """,
                (cid, name, desc, int(time.time())),
            )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def list_episodes() -> list[dict]:
    conn = get_db()
    try:
        cur = conn.execute(
            "SELECT * FROM episodes ORDER BY created_at DESC"
        )
        return [_row_to_dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def create_shots(episode_id: str, shots_list: list[dict]) -> None:
    conn = get_db()
    try:
        for shot in shots_list:
            sid = shot.get("id") or f"{episode_id}-s{int(shot['sequence']):03d}"
            characters_used = shot.get("characters_used") or []
            if isinstance(characters_used, list):
                characters_used = json.dumps(characters_used)
            conn.execute(
                """
                INSERT INTO shots (
                    id, episode_id, sequence, description,
                    image_prompt, video_prompt, model, duration_sec,
                    dialogue, characters_used,
                    emotional_tone, cinematic_reference, motion_intent,
                    sound_design, transition_to_next
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sid,
                    episode_id,
                    int(shot["sequence"]),
                    shot.get("description"),
                    shot.get("image_prompt"),
                    shot.get("video_prompt"),
                    shot.get("model"),
                    int(shot.get("duration_sec") or 6),
                    shot.get("dialogue"),
                    characters_used,
                    shot.get("emotional_tone"),
                    shot.get("cinematic_reference"),
                    shot.get("motion_intent"),
                    shot.get("sound_design"),
                    shot.get("transition_to_next"),
                ),
            )
        conn.commit()
    finally:
        conn.close()


def update_shot(shot_id: str, **kwargs) -> None:
    if not kwargs:
        return
    cols = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [shot_id]
    conn = get_db()
    try:
        conn.execute(f"UPDATE shots SET {cols} WHERE id = ?", values)
        conn.commit()
    finally:
        conn.close()


def get_shots(episode_id: str) -> list[dict]:
    conn = get_db()
    try:
        cur = conn.execute(
            "SELECT * FROM shots WHERE episode_id = ? ORDER BY sequence ASC",
            (episode_id,),
        )
        rows = [_row_to_dict(r) for r in cur.fetchall()]
        for r in rows:
            if r.get("characters_used"):
                try:
                    r["characters_used"] = json.loads(r["characters_used"])
                except (json.JSONDecodeError, TypeError):
                    pass
        return rows
    finally:
        conn.close()


def get_pending_video_jobs() -> list[dict]:
    conn = get_db()
    try:
        cur = conn.execute(
            """
            SELECT * FROM shots
            WHERE video_status IN ('running', 'queued')
            """
        )
        return [_row_to_dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def upsert_character(
    char_id: str,
    name: str,
    description: str | None,
    voice_speaker: str | None = None,
    ref_images: str | dict | None = None,
) -> None:
    now = int(time.time())
    if isinstance(ref_images, dict):
        ref_images = json.dumps(ref_images)
    conn = get_db()
    try:
        conn.execute(
            """
            INSERT INTO characters (id, name, description, voice_speaker, ref_images, created_at)
            VALUES (?, ?, ?, ?, COALESCE(?, '{}'), ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                description = COALESCE(excluded.description, characters.description),
                voice_speaker = COALESCE(excluded.voice_speaker, characters.voice_speaker),
                ref_images = COALESCE(NULLIF(excluded.ref_images, '{}'), characters.ref_images)
            """,
            (char_id, name, description, voice_speaker, ref_images, now),
        )
        conn.commit()
    finally:
        conn.close()


def get_character(character_id: str) -> dict | None:
    conn = get_db()
    try:
        cur = conn.execute(
            "SELECT * FROM characters WHERE id = ?", (character_id,)
        )
        return _row_to_dict(cur.fetchone())
    finally:
        conn.close()


def get_all_characters() -> list[dict]:
    conn = get_db()
    try:
        cur = conn.execute("SELECT * FROM characters ORDER BY name ASC")
        return [_row_to_dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def create_narration(episode_id: str, position: str, script: str) -> str:
    nid = str(uuid.uuid4())
    conn = get_db()
    try:
        conn.execute(
            """
            INSERT INTO narration (id, episode_id, position, script, voice_status)
            VALUES (?, ?, ?, ?, 'pending')
            """,
            (nid, episode_id, position, script),
        )
        conn.commit()
        return nid
    finally:
        conn.close()


def update_narration(narration_id: str, **kwargs) -> None:
    if not kwargs:
        return
    cols = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [narration_id]
    conn = get_db()
    try:
        conn.execute(f"UPDATE narration SET {cols} WHERE id = ?", values)
        conn.commit()
    finally:
        conn.close()


def create_dubs(episode_id: str, language_codes: list[str]) -> None:
    conn = get_db()
    try:
        for code in language_codes:
            did = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO dubs (id, episode_id, language_code, status)
                VALUES (?, ?, ?, 'pending')
                """,
                (did, episode_id, code),
            )
        conn.commit()
    finally:
        conn.close()


def update_dub(dub_id: str, **kwargs) -> None:
    if not kwargs:
        return
    cols = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [dub_id]
    conn = get_db()
    try:
        conn.execute(f"UPDATE dubs SET {cols} WHERE id = ?", values)
        conn.commit()
    finally:
        conn.close()


def log_cost(episode_id: str | None, service: str, amount_usd: float) -> None:
    now = int(time.time())
    conn = get_db()
    try:
        conn.execute(
            """
            INSERT INTO cost_log (episode_id, service, amount_usd, logged_at)
            VALUES (?, ?, ?, ?)
            """,
            (episode_id, service, amount_usd, now),
        )
        conn.commit()
    finally:
        conn.close()


def get_episode_cost(episode_id: str) -> float:
    conn = get_db()
    try:
        cur = conn.execute(
            "SELECT COALESCE(SUM(amount_usd), 0) AS t FROM cost_log WHERE episode_id = ?",
            (episode_id,),
        )
        row = cur.fetchone()
        return float(row["t"] if row else 0.0)
    finally:
        conn.close()
