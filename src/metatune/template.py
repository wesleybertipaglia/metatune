"""Editable JSON metadata templates.

Two shapes are accepted:

Flat (applied to every selected file)::

    {"artist": "Pink Floyd", "album": "The Wall", "genre": "Rock"}

Structured (shared defaults + per-track overrides)::

    {
      "defaults": {"artist": "...", "album": "..."},
      "tracks": {
        "01-song.mp3": {"title": "...", "track": "1"},
        "02-other.mp3": {"title": "...", "track": "2"}
      }
    }
"""

from __future__ import annotations

import json
from pathlib import Path

from metatune.metadata import METADATA_FIELDS

TEMPLATE_VERSION = 1


def default_template() -> dict:
    return {
        "$schema": "metatune-template",
        "version": TEMPLATE_VERSION,
        "defaults": {
            "title": "",
            "artist": "",
            "album": "",
            "albumartist": "",
            "genre": "",
            "year": "",
            "track": "",
            "track_total": "",
            "disc": "",
            "disc_total": "",
            "composer": "",
            "comment": "",
            "cover": "",
        },
        "tracks": {},
    }


def generate_template(output: str | Path, force: bool = False) -> Path:
    """Write a blank editable template to *output*."""
    path = Path(output).expanduser()
    if path.exists() and not force:
        raise FileExistsError(f"Template already exists: {path} (use --force to overwrite).")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(default_template(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def _clean(data: dict) -> dict:
    return {k: str(v) for k, v in data.items() if k in METADATA_FIELDS and v not in (None, "")}


def load_template(path: str | Path) -> tuple[dict, dict[str, dict]]:
    """Load a template file.

    Returns ``(defaults, per_file_overrides)`` where both are plain dicts
    keyed by the canonical metadata field names.
    """
    template_path = Path(path).expanduser()
    if not template_path.is_file():
        raise FileNotFoundError(f"Template file not found: {template_path}")
    try:
        raw = json.loads(template_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON template '{template_path}': {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError("Template root must be a JSON object.")

    if "defaults" in raw or "tracks" in raw:
        defaults = _clean(raw.get("defaults") or {})
        tracks_raw = raw.get("tracks") or {}
        if not isinstance(tracks_raw, dict):
            raise ValueError("Template 'tracks' must be an object mapping filename -> metadata.")
        per_file = {name: _clean(meta) for name, meta in tracks_raw.items() if isinstance(meta, dict)}
    else:
        # Flat template: every known key is a default for all files.
        defaults = _clean(raw)
        per_file = {}
    return defaults, per_file
