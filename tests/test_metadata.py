"""Tests for metatune.metadata using mocked mutagen MP3 objects."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from metatune.metadata import (
    Metadata,
    apply_metadata,
    apply_to_directory,
    read_metadata,
)


def _fake_audio():
    audio = MagicMock()
    tags: dict = {}

    def getall(key):
        value = tags.get(key)
        return [value] if value is not None else []

    audio.tags = MagicMock()
    audio.tags.__setitem__.side_effect = lambda k, v: tags.__setitem__(k, v)
    audio.tags.__getitem__.side_effect = lambda k: tags.__getitem__(k)
    audio.tags.get.side_effect = lambda k, default=None: tags.get(k, default)
    audio.tags.getall.side_effect = getall
    audio.tags.clear.side_effect = lambda: tags.clear()
    return audio, tags


def test_metadata_from_dict_ignores_unknown_keys():
    meta = Metadata.from_dict({"artist": "X", "unknown": "zzz", "title": ""})
    assert meta.artist == "X"
    assert meta.title == ""


def test_apply_metadata_sets_frames(tmp_path):
    song = tmp_path / "song.mp3"
    song.write_bytes(b"fake")
    audio, tags = _fake_audio()
    with patch("metatune.metadata.MP3", return_value=audio):
        assert apply_metadata(song, {"artist": "A", "album": "B", "title": "T"}) is True
    assert str(tags["TPE1"].text[0]) == "A"
    assert str(tags["TALB"].text[0]) == "B"
    audio.save.assert_called_once()


def test_apply_metadata_dry_run_does_not_save(tmp_path):
    song = tmp_path / "song.mp3"
    song.write_bytes(b"fake")
    audio, _ = _fake_audio()
    with patch("metatune.metadata.MP3", return_value=audio):
        apply_metadata(song, {"artist": "A"}, dry_run=True)
    audio.save.assert_not_called()


def test_apply_metadata_rejects_empty(tmp_path):
    song = tmp_path / "song.mp3"
    song.write_bytes(b"fake")
    with pytest.raises(ValueError, match="No metadata"):
        apply_metadata(song, {})


def test_apply_metadata_rejects_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        apply_metadata(tmp_path / "nope.mp3", {"artist": "A"})


def test_apply_metadata_rejects_unsupported_extension(tmp_path):
    song = tmp_path / "song.wav"
    song.write_bytes(b"fake")
    with pytest.raises(ValueError, match="Unsupported"):
        apply_metadata(song, {"artist": "A"})


def test_apply_metadata_track_total_combined(tmp_path):
    song = tmp_path / "song.mp3"
    song.write_bytes(b"fake")
    audio, tags = _fake_audio()
    with patch("metatune.metadata.MP3", return_value=audio):
        apply_metadata(song, {"track": "3", "track_total": "12"})
    assert str(tags["TRCK"].text[0]) == "3/12"


def test_apply_to_directory_merges_per_file(tmp_path):
    for name in ("a.mp3", "b.mp3"):
        (tmp_path / name).write_bytes(b"fake")
    seen: dict[str, dict] = {}

    def fake_apply(file, metadata, **kwargs):
        meta = metadata if isinstance(metadata, Metadata) else Metadata.from_dict(metadata)
        seen[Path(file).name] = meta.to_dict()
        return True

    with patch("metatune.metadata.apply_metadata", side_effect=fake_apply):
        result = apply_to_directory(
            tmp_path,
            {"artist": "Band", "album": "Rec"},
            per_file={"b.mp3": {"title": "Second", "track": "2"}},
        )
    assert result["updated"] == ["a.mp3", "b.mp3"]
    assert seen["a.mp3"]["artist"] == "Band"
    assert seen["b.mp3"]["title"] == "Second"
    assert seen["b.mp3"]["artist"] == "Band"


def test_read_metadata_empty_tags(tmp_path):
    song = tmp_path / "song.mp3"
    song.write_bytes(b"fake")
    audio = MagicMock()
    audio.tags = None
    with patch("metatune.metadata.MP3", return_value=audio):
        assert read_metadata(song) == {}
