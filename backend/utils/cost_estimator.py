"""Estimate USD cost from a scripted episode (v3 spec)."""

from __future__ import annotations

IMAGE_COST_USD = 0.04
VIDEO_COSTS_USD = {
    "seedance": 0.015,
    "kling": 0.05,
    "wan": 0.01,
    "veo-lite": 0.025,
}
SARVAM_TTS_USD = 0.0002
SARVAM_DUB_USD = 0.012


def estimate(
    shot_list: list[dict],
    new_characters: list[dict] | None = None,
    dub_language_count: int = 9,
    episode_duration_sec: float | None = None,
) -> dict:
    """
    Returns itemised cost breakdown + total.
    new_characters: entries with is_new True (each needs 6 reference images).
    """
    new_characters = new_characters or []
    if episode_duration_sec is None:
        episode_duration_sec = sum(float(s.get("duration_sec") or 6) for s in shot_list)

    n_new = len(new_characters)
    char_images_cost = n_new * 6 * IMAGE_COST_USD

    n_shots = len(shot_list)
    scene_images_cost = n_shots * IMAGE_COST_USD

    video_breakdown: dict[str, dict[str, float]] = {}
    video_total = 0.0
    for shot in shot_list:
        model = (shot.get("model") or "seedance").lower()
        dur = float(shot.get("duration_sec") or 6)
        rate = VIDEO_COSTS_USD.get(model, VIDEO_COSTS_USD["seedance"])
        line_cost = rate * dur
        video_total += line_cost
        bucket = video_breakdown.setdefault(
            model, {"shots": 0, "seconds": 0.0, "usd": 0.0}
        )
        bucket["shots"] += 1
        bucket["seconds"] += dur
        bucket["usd"] += line_cost

    narrator_segments = 2
    dialogue_lines = sum(
        1 for s in shot_list if s.get("dialogue") not in (None, "", [])
    )
    tts_units = narrator_segments + dialogue_lines
    voices_cost = tts_units * SARVAM_TTS_USD

    dub_minutes = max(episode_duration_sec / 60.0, 0.01)
    dubs_cost = dub_language_count * dub_minutes * SARVAM_DUB_USD

    script_cost = 0.01

    lines = [
        {
            "label": "Claude — script",
            "usd": round(script_cost, 4),
        },
        {
            "label": f"Character images ({n_new} new × 6 angles)",
            "usd": round(char_images_cost, 4),
        },
        {
            "label": f"Scene images ({n_shots} shots)",
            "usd": round(scene_images_cost, 4),
        },
    ]
    for model, data in sorted(video_breakdown.items()):
        lines.append(
            {
                "label": f"Video — {model} ({int(data['shots'])} shots, {int(data['seconds'])}s)",
                "usd": round(data["usd"], 4),
            }
        )
    lines.append(
        {
            "label": "Voices + narration (approx)",
            "usd": round(voices_cost, 4),
        }
    )
    lines.append(
        {
            "label": f"Dubs × {dub_language_count} languages (approx)",
            "usd": round(dubs_cost, 4),
        }
    )

    total = sum(x["usd"] for x in lines)
    return {
        "lines": lines,
        "total_usd": round(total, 2),
        "video_by_model": video_breakdown,
    }
