"""Shot and episode mutation routes — Sprint 3."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from backend import db

bp = Blueprint("shots_api", __name__)

SHOT_EDITABLE = {"description", "model", "duration_sec", "dialogue", "image_prompt", "video_prompt"}


@bp.patch("/shots/<shot_id>")
def patch_shot(shot_id: str):
    body = request.get_json(silent=True) or {}
    updates = {k: v for k, v in body.items() if k in SHOT_EDITABLE}
    if not updates:
        return jsonify({"error": "no editable fields provided"}), 400
    if "duration_sec" in updates:
        try:
            updates["duration_sec"] = int(updates["duration_sec"])
        except (ValueError, TypeError):
            return jsonify({"error": "duration_sec must be an integer"}), 400
    db.update_shot(shot_id, **updates)
    return jsonify({"ok": True, "shot_id": shot_id, "updated": updates})


@bp.delete("/shots/<shot_id>")
def delete_shot(shot_id: str):
    conn = db.get_db()
    try:
        conn.execute("DELETE FROM shots WHERE id = ?", (shot_id,))
        conn.commit()
    finally:
        conn.close()
    return jsonify({"ok": True, "shot_id": shot_id})


@bp.patch("/episodes/<episode_id>")
def patch_episode(episode_id: str):
    body = request.get_json(silent=True) or {}
    title = (body.get("title") or "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400
    conn = db.get_db()
    try:
        conn.execute("UPDATE episodes SET title = ? WHERE id = ?", (title, episode_id))
        conn.commit()
    finally:
        conn.close()
    return jsonify({"ok": True, "episode_id": episode_id, "title": title})
