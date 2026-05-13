"""OpenRouter image generation — character ref sheets and scene first-frames."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import requests

from backend.utils.file_writer import characters_dir, episode_dir
from backend.utils.job_queue import submit
from backend.utils.prompt_builder import resolve_prompt

IMAGE_MODEL = "google/gemini-2.5-flash-preview-05-20"

# 6 canonical angles for every new character
CHARACTER_ANGLES = [
    ("front",           "facing camera directly, full body, neutral expression, plain white background"),
    ("three_quarter",   "three-quarter view, slight turn right, full body, plain white background"),
    ("side",            "side profile, full body, plain white background"),
    ("back",            "back view, full body, plain white background"),
    ("face_closeup",    "face close-up, looking at camera, warm expression, plain white background"),
    ("full_body_arms",  "full body, arms slightly out, welcoming pose, plain white background"),
]


def _openrouter_image(prompt: str, *, size: str = "1792x1024") -> str:
    """
    Call OpenRouter image generations endpoint.
    Returns the image URL from the response.
    Raises RuntimeError on HTTP error or missing URL.
    """
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    payload: dict[str, Any] = {
        "model": IMAGE_MODEL,
        "prompt": prompt,
        "size": size,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    last_err: Exception | None = None
    for attempt in range(3):
        try:
            r = requests.post(
                "https://openrouter.ai/api/v1/images/generations",
                json=payload,
                headers=headers,
                timeout=120,
            )
            if r.status_code >= 500:
                raise RuntimeError(f"OpenRouter 5xx: {r.status_code}")
            if r.status_code >= 400:
                raise RuntimeError(f"OpenRouter error {r.status_code}: {r.text[:300]}")
            data = r.json()
            url = (data.get("data") or [{}])[0].get("url")
            if not url:
                raise RuntimeError(f"No URL in response: {data}")
            return url
        except Exception as exc:
            last_err = exc
            if attempt < 2:
                time.sleep(2 ** attempt)

    raise RuntimeError(f"Image generation failed after retries: {last_err}")


def _generate_one_angle(
    character: dict,
    angle_name: str,
    angle_desc: str,
    dest_path: Path,
) -> str:
    """Generate a single angle image and write it to *dest_path*. Returns local path."""
    art_style = os.environ.get(
        "ART_STYLE",
        "soft watercolour illustration, warm pastel colours, child-friendly, storybook aesthetic",
    )
    desc = character.get("description") or character.get("name", "a cartoon character")
    prompt = (
        f"{art_style}, character model sheet, {desc}, "
        f"{angle_desc}, clean illustration, white background"
    )
    url = _openrouter_image(prompt, size="1024x1024")

    from backend.utils.file_writer import download_url
    download_url(url, dest_path)
    return str(dest_path)


def generate_character_images(character: dict) -> dict[str, str]:
    """
    Generate 6 reference images for *character* in parallel.
    character dict must have keys: id, name, description.
    Returns { angle_name: local_path } for all 6 angles.
    Saves images to OUTPUT_DIR/characters/{character_id}/{angle}.png
    """
    char_id = character.get("id") or character.get("name", "unknown").lower().replace(" ", "-")
    char_dir = characters_dir() / char_id
    char_dir.mkdir(parents=True, exist_ok=True)

    futures = {}
    for angle_name, angle_desc in CHARACTER_ANGLES:
        dest = char_dir / f"{angle_name}.png"
        futures[angle_name] = submit(
            _generate_one_angle,
            character,
            angle_name,
            angle_desc,
            dest,
        )

    results: dict[str, str] = {}
    errors: list[str] = []
    for angle_name, fut in futures.items():
        try:
            results[angle_name] = fut.result(timeout=180)
        except Exception as exc:
            errors.append(f"{angle_name}: {exc}")

    if errors:
        raise RuntimeError(f"Some angles failed: {'; '.join(errors)}")

    return results


def generate_scene_image(shot: dict, all_characters: dict) -> str:
    """
    Generate the first-frame scene image for a single shot.
    Returns local path.
    all_characters: dict keyed by lowercase name → character row dict.
    """
    raw_prompt = shot.get("image_prompt") or shot.get("description") or "cartoon scene"
    resolved = resolve_prompt(raw_prompt, all_characters)
    prompt = resolved["resolved_prompt"]

    url = _openrouter_image(prompt, size="1792x1024")

    ep_id = shot.get("episode_id", "unknown")
    seq = shot.get("sequence", 0)
    slug = _slugify(shot.get("description") or "scene")[:30]
    dest = episode_dir(ep_id) / "frames" / f"{int(seq):02d}-{slug}.png"

    from backend.utils.file_writer import download_url
    download_url(url, dest)
    return str(dest)


def _slugify(text: str) -> str:
    import re
    s = (text or "").lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "scene"
