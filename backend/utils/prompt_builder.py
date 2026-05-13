"""Resolve [STYLE] and [CHAR:name] tokens in image/video prompts."""

from __future__ import annotations

import os
import re


def resolve_prompt(
    raw_prompt: str,
    characters: dict[str, dict],
) -> dict:
    """
    Replace tokens in *raw_prompt*:
      [STYLE]      → ART_STYLE env var
      [CHAR:name]  → character description (for prompt text)

    Parameters
    ----------
    raw_prompt  : the image_prompt or video_prompt string from the shot
    characters  : dict keyed by lowercase character name →
                  { "description": str, "ref_images": dict, ... }

    Returns
    -------
    {
        "resolved_prompt": str,
        "char_refs": { name: [image_path, ...] }   # ref image paths, may be empty
    }
    """
    art_style = os.environ.get(
        "ART_STYLE",
        "soft watercolour illustration, warm pastel colours, child-friendly, storybook aesthetic",
    )
    prompt = raw_prompt.replace("[STYLE]", art_style)

    char_refs: dict[str, list[str]] = {}

    def _replace_char(m: re.Match) -> str:
        name = m.group(1).strip()
        key = name.lower()
        char = characters.get(key) or {}
        desc = char.get("description") or name

        # Collect any ref image paths stored for this character
        ref_images: dict = {}
        raw_refs = char.get("ref_images")
        if isinstance(raw_refs, str):
            import json
            try:
                ref_images = json.loads(raw_refs)
            except Exception:
                ref_images = {}
        elif isinstance(raw_refs, dict):
            ref_images = raw_refs

        paths = [p for p in ref_images.values() if p]
        if paths:
            char_refs[name] = paths

        return desc

    prompt = re.sub(r"\[CHAR:([^\]]+)\]", _replace_char, prompt)
    return {"resolved_prompt": prompt, "char_refs": char_refs}
