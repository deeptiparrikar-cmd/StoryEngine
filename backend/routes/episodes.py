"""Episode API routes — Sprints 1-4."""

from __future__ import annotations

import json
import os
import re
import time
from flask import Blueprint, jsonify, request

from backend import db
from backend.agents import script_agent
from backend.utils import cost_estimator

bp = Blueprint("episodes_api", __name__)


def _episode_id_from_story(story: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", story)[:5]
    base = "-".join(w.lower() for w in words) if words else "episode"
    return f"{base}-{int(time.time())}"


def _dub_language_count() -> int:
    raw = os.environ.get("DUB_LANGUAGES", "")
    codes = [c.strip() for c in raw.split(",") if c.strip()]
    return len(codes) if codes else 9


def _max_spend() -> float:
    try:
        return float(os.environ.get("MAX_SPEND_PER_EPISODE_USD", "6.00"))
    except ValueError:
        return 6.0


@bp.post("/episodes/new")
def episodes_new():
    body = request.get_json(silent=True) or {}
    story = (body.get("story") or "").strip()
    if not story:
        return jsonify({"error": "story is required"}), 400

    episode_id = _episode_id_from_story(story)
    db.create_episode(episode_id, "", story)

    try:
        existing = db.get_all_characters()
        plan = script_agent.plan_episode(
            story,
            [{"name": c.get("name"), "description": c.get("description")} for c in existing],
        )
    except Exception as e:
        db.update_episode_status(episode_id, "draft")
        return jsonify({"error": str(e), "episode_id": episode_id}), 502

    shots = plan.get("shots") or []
    new_chars = [c for c in (plan.get("characters_needed") or []) if c.get("is_new")]
    duration_sec = sum(int(s.get("duration_sec") or 6) for s in shots)
    estimate = cost_estimator.estimate(
        shots,
        new_chars,
        _dub_language_count(),
        float(duration_sec),
    )

    try:
        db.save_scripted_episode(episode_id, plan, estimate)
    except Exception as e:
        return jsonify({"error": str(e), "episode_id": episode_id}), 500

    episode = db.get_episode(episode_id)
    shots_rows = db.get_shots(episode_id)
    max_spend = _max_spend()
    over_budget = float(estimate["total_usd"]) > max_spend

    return jsonify(
        {
            "episode": episode,
            "shot_list": shots_rows,
            "shots": shots_rows,
            "plan": {
                "characters_needed": plan.get("characters_needed"),
                "narrator_intro": plan.get("narrator_intro"),
                "narrator_outro": plan.get("narrator_outro"),
            },
            "cost_estimate": estimate,
            "max_spend_usd": max_spend,
            "over_budget": over_budget,
        }
    )


@bp.get("/episodes")
def episodes_list():
    rows = db.list_episodes()
    return jsonify({"episodes": rows})


@bp.get("/episodes/<episode_id>")
def episode_detail(episode_id: str):
    episode = db.get_episode(episode_id)
    if not episode:
        return jsonify({"error": "not found"}), 404
    shots = db.get_shots(episode_id)
    plan = {}
    raw = episode.get("plan_json")
    if raw:
        try:
            plan = json.loads(raw)
        except json.JSONDecodeError:
            plan = {}
    estimate = plan.get("cost_estimate")
    if not estimate:
        new_chars = [c for c in (plan.get("characters_needed") or []) if c.get("is_new")]
        duration_sec = sum(int(s.get("duration_sec") or 6) for s in shots)
        estimate = cost_estimator.estimate(
            shots,
            new_chars,
            _dub_language_count(),
            float(duration_sec),
        )
    max_spend = _max_spend()
    plan_out = {k: v for k, v in plan.items() if k != "cost_estimate"}
    return jsonify(
        {
            "episode": episode,
            "shots": shots,
            "plan": plan_out,
            "cost_estimate": estimate,
            "max_spend_usd": max_spend,
            "over_budget": float(estimate["total_usd"]) > max_spend,
        }
    )


# ── Sprint 4: Generate ─────────────────────────────────────────────────────

def _run_character_generation(episode_id: str, new_characters: list[dict]) -> None:
    """Background task: generate 6-angle ref images for each new character."""
    from backend.agents.image_agent import generate_character_images

    db.update_episode_status(episode_id, "generating")
    all_ok = True

    for ch in new_characters:
        char_id = ch.get("id") or re.sub(r"[^a-z0-9]+", "-", (ch.get("name") or "").lower()).strip("-")
        try:
            ref_paths = generate_character_images({"id": char_id, **ch})
            db.upsert_character(
                char_id,
                ch.get("name", char_id),
                ch.get("description"),
                ref_images=ref_paths,
            )
        except Exception as exc:
            all_ok = False
            # Log but continue with remaining characters
            print(f"[image_agent] character {char_id} failed: {exc}")

    if all_ok:
        db.update_episode_status(episode_id, "scripted")   # ready for video sprint
    else:
        db.update_episode_status(episode_id, "draft")


@bp.post("/episodes/<episode_id>/generate")
def episode_generate(episode_id: str):
    episode = db.get_episode(episode_id)
    if not episode:
        return jsonify({"error": "episode not found"}), 404

    # Pull new characters from stored plan_json
    plan: dict = {}
    raw = episode.get("plan_json") if isinstance(episode, dict) else None
    if raw:
        try:
            plan = json.loads(raw)
        except json.JSONDecodeError:
            plan = {}

    new_chars = [c for c in (plan.get("characters_needed") or []) if c.get("is_new")]

    db.update_episode_status(episode_id, "approved")

    from backend.utils.job_queue import submit
    submit(_run_character_generation, episode_id, new_chars)

    return jsonify(
        {
            "ok": True,
            "episode_id": episode_id,
            "status": "approved",
            "characters_queued": len(new_chars),
            "message": f"Generating {len(new_chars)} character(s) in background.",
        }
    ), 202


@bp.get("/episodes/<episode_id>/generate-status")
def episode_generate_status(episode_id: str):
    """Lightweight poll used by the frontend during Sprint 4 generation."""
    episode = db.get_episode(episode_id)
    if not episode:
        return jsonify({"error": "not found"}), 404
    return jsonify(
        {
            "episode_id": episode_id,
            "status": episode.get("status"),
        }
    )
