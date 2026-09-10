"""Core ID3 tagging logic for MP3 files."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from mutagen.id3 import (
    APIC,
    COMM,
    ID3,
    TALB,
    TCOM,
    TCON,
    TDRC,
    TIT2,
    TPE1,
    TPE2,
    TPOS,
    TRCK,
)
from mutagen.mp3 import MP3

from metatune.utils import discover_files, is_supported

# Canonical metadata keys accepted everywhere (CLI flags, template files).
METADATA_FIELDS = (
    "title",
    "artist",
    "album",
    "albumartist",
    "genre",
    "year",
    "track",
    "track_total",
    "disc",
    "disc_total",
    "composer",
    "comment",
    "cover",
)


@dataclass
class Metadata:
    """A normalized set of tags to write to a file."""

    title: str = ""
    artist: str = ""
    album: str = ""
    albumartist: str = ""
    genre: str = ""
    year: str = ""
    track: str = ""
    track_total: str = ""
    disc: str = ""
    disc_total: str = ""
    composer: str = ""
    comment: str = ""
    cover: str = ""  # path to a JPEG/PNG image file

    def to_dict(self) -> dict[str, str]:
        return {f: getattr(self, f) for f in METADATA_FIELDS}

    @classmethod
    def from_dict(cls, data: dict) -> "Metadata":
        known = {k: str(v) for k, v in data.items() if k in METADATA_FIELDS and v not in (None, "")}
        return cls(**known)

    def is_empty(self) -> bool:
        return not any(getattr(self, f) for f in METADATA_FIELDS)


def _combined(number: str, total: str) -> str:
    number, total = number.strip(), total.strip()
    if number and total:
        return f"{number}/{total}"
    return number or total


def load_cover_bytes(cover_path: str | Path) -> tuple[bytes, str]:
    """Read a cover image, returning (data, mime)."""
    path = Path(cover_path).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"Cover image not found: {path}")
    suffix = path.suffix.lower()
    if suffix == ".png":
        mime = "image/png"
    elif suffix in (".jpg", ".jpeg"):
        mime = "image/jpeg"
    elif suffix == ".webp":
        mime = "image/webp"
    else:
        raise ValueError(f"Unsupported cover format '{suffix}' (use .jpg/.png/.webp).")
    return path.read_bytes(), mime


def apply_metadata(
    file: str | Path,
    metadata: Metadata | dict,
    clear_existing: bool = False,
    dry_run: bool = False,
) -> bool:
    """Write *metadata* to a single MP3 file.

    Returns True on success. Raises on invalid input / unreadable file.
    With ``dry_run=True`` tags are validated but nothing is saved.
    """
    path = Path(file).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")
    if not is_supported(path):
        raise ValueError(f"Unsupported file type '{path.suffix}' (only .mp3 supported).")

    meta = metadata if isinstance(metadata, Metadata) else Metadata.from_dict(metadata)
    if meta.is_empty():
        raise ValueError("No metadata provided (all fields empty).")

    audio = MP3(path, ID3=ID3)
    if audio.tags is None:
        audio.add_tags()
    if clear_existing:
        audio.tags.clear()

    tags = audio.tags
    assert tags is not None

    if meta.title:
        tags["TIT2"] = TIT2(encoding=3, text=meta.title)
    if meta.artist:
        tags["TPE1"] = TPE1(encoding=3, text=meta.artist)
    if meta.album:
        tags["TALB"] = TALB(encoding=3, text=meta.album)
    if meta.albumartist:
        tags["TPE2"] = TPE2(encoding=3, text=meta.albumartist)
    if meta.genre:
        tags["TCON"] = TCON(encoding=3, text=meta.genre)
    if meta.year:
        tags["TDRC"] = TDRC(encoding=3, text=str(meta.year))
    track_value = _combined(meta.track, meta.track_total)
    if track_value:
        tags["TRCK"] = TRCK(encoding=3, text=track_value)
    disc_value = _combined(meta.disc, meta.disc_total)
    if disc_value:
        tags["TPOS"] = TPOS(encoding=3, text=disc_value)
    if meta.composer:
        tags["TCOM"] = TCOM(encoding=3, text=meta.composer)
    if meta.comment:
        tags["COMM"] = COMM(encoding=3, lang="eng", desc="", text=meta.comment)
    if meta.cover:
        data, mime = load_cover_bytes(meta.cover)
        tags["APIC"] = APIC(encoding=3, mime=mime, type=3, desc="Cover", data=data)

    if not dry_run:
        audio.save()
    return True


def apply_to_directory(
    directory: str | Path,
    metadata: Metadata | dict,
    recursive: bool = False,
    pattern: str = "*.mp3",
    clear_existing: bool = False,
    dry_run: bool = False,
    per_file: dict[str, dict] | None = None,
) -> dict[str, list[str]]:
    """Apply *metadata* to every matching MP3 in *directory*.

    *per_file* optionally maps ``filename -> extra metadata`` that is merged
    over the base metadata (used by templates with per-track overrides).

    Returns ``{"updated": [...], "failed": [...], "skipped": [...]}``.
    """
    base = metadata if isinstance(metadata, Metadata) else Metadata.from_dict(metadata)
    result: dict[str, list[str]] = {"updated": [], "failed": [], "skipped": []}
    files = discover_files(Path(directory).expanduser(), recursive=recursive, pattern=pattern)

    for file in files:
        merged = Metadata.from_dict(base.to_dict())
        if per_file and file.name in per_file:
            for key, value in per_file[file.name].items():
                if key in METADATA_FIELDS and value not in (None, ""):
                    setattr(merged, key, str(value))
        try:
            if merged.is_empty():
                result["skipped"].append(file.name)
                continue
            apply_metadata(file, merged, clear_existing=clear_existing, dry_run=dry_run)
            result["updated"].append(file.name)
        except Exception:
            result["failed"].append(file.name)
    return result


def read_metadata(file: str | Path) -> dict[str, str]:
    """Read ID3 tags from an MP3 file into a plain dict."""
    path = Path(file).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")
    audio = MP3(path, ID3=ID3)
    tags = audio.tags
    if tags is None:
        return {}

    def _text(frame_name: str) -> str:
        frame = tags.get(frame_name)
        if frame is None or not getattr(frame, "text", None):
            return ""
        return str(frame.text[0])

    data: dict[str, str] = {
        "title": _text("TIT2"),
        "artist": _text("TPE1"),
        "album": _text("TALB"),
        "albumartist": _text("TPE2"),
        "genre": _text("TCON"),
        "year": _text("TDRC") or _text("TYER"),
        "composer": _text("TCOM"),
        "track": "",
        "track_total": "",
        "disc": "",
        "disc_total": "",
        "comment": "",
        "cover": "",
    }
    # Split "3/12" style combined frames.
    for key, frame_name in (("track", "TRCK"), ("disc", "TPOS")):
        raw = _text(frame_name)
        if "/" in raw:
            number, _, total = raw.partition("/")
            data[key], data[f"{key}_total"] = number.strip(), total.strip()
        else:
            data[key] = raw
    comms = tags.getall("COMM")
    if comms and getattr(comms[0], "text", None):
        data["comment"] = str(comms[0].text[0])
    apics = tags.getall("APIC")
    if apics:
        data["cover"] = f"{apics[0].mime} ({len(apics[0].data)} bytes embedded)"
    return {k: v for k, v in data.items() if v}
