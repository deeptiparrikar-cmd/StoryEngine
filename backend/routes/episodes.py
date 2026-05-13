"""Sprint 1 episode API: create from story + list episodes."""

from __future__ import annotations

import os
import re
import time
import json
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
