"""Download remote URLs to local disk paths."""

from __future__ import annotations

import os
import time
from pathlib import Path

import requests


def download_url(url: str, dest_path: str | Path, *, retries: int = 2) -> Path:
    """
    Download *url* to *dest_path*, creating parent directories as needed.
    Returns the resolved Path on success, raises RuntimeError on failure.
    """
    dest = Path(dest_path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    last_err: Exception | None = None
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, timeout=120, stream=True)
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=65536):
                    f.write(chunk)
            return dest
        except Exception as exc:
            last_err = exc
            if attempt < retries:
                time.sleep(2 ** attempt)

    raise RuntimeError(f"Failed to download {url}: {last_err}")


def episode_dir(episode_id: str) -> Path:
    """Return the root output folder for an episode, creating it if needed."""
    base = Path(os.environ.get("OUTPUT_DIR", "episodes"))
    path = base / episode_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def characters_dir() -> Path:
    """Return the shared characters folder, creating it if needed."""
    base = Path(os.environ.get("OUTPUT_DIR", "episodes"))
    path = base / "characters"
    path.mkdir(parents=True, exist_ok=True)
    return path
