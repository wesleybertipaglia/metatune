"""Tests for template generation / loading."""

from __future__ import annotations

import json

import pytest

from metatune.template import default_template, generate_template, load_template


def test_generate_and_load_roundtrip(tmp_path):
    out = tmp_path / "tpl.json"
    generate_template(out)
    assert out.is_file()
    defaults, per_file = load_template(out)
    assert defaults == {}
    assert per_file == {}


def test_generate_refuses_overwrite_without_force(tmp_path):
    out = tmp_path / "tpl.json"
    generate_template(out)
    with pytest.raises(FileExistsError):
        generate_template(out)
    generate_template(out, force=True)  # should not raise


def test_load_flat_template(tmp_path):
    tpl = tmp_path / "flat.json"
    tpl.write_text(json.dumps({"artist": "A", "album": "B", "nope": 1}))
    defaults, per_file = load_template(tpl)
    assert defaults == {"artist": "A", "album": "B"}
    assert per_file == {}


def test_load_structured_template(tmp_path):
    tpl = tmp_path / "s.json"
    tpl.write_text(
        json.dumps(
            {
                "defaults": {"artist": "Band", "album": "Rec"},
                "tracks": {"01.mp3": {"title": "One", "track": "1"}},
            }
        )
    )
    defaults, per_file = load_template(tpl)
    assert defaults["artist"] == "Band"
    assert per_file["01.mp3"]["title"] == "One"


def test_load_invalid_json(tmp_path):
    tpl = tmp_path / "bad.json"
    tpl.write_text("{not json")
    with pytest.raises(ValueError, match="Invalid JSON"):
        load_template(tpl)


def test_load_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_template(tmp_path / "missing.json")


def test_default_template_has_expected_keys():
    tpl = default_template()
    assert "defaults" in tpl and "tracks" in tpl
    assert "artist" in tpl["defaults"]
