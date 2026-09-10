"""Tests for file discovery utils and CLI wiring."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from metatune.cli import build_parser, main
from metatune.utils import discover_files


def test_discover_files_non_recursive(tmp_path):
    (tmp_path / "a.mp3").write_bytes(b"x")
    (tmp_path / "b.mp3").write_bytes(b"x")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "c.mp3").write_bytes(b"x")
    assert len(discover_files(tmp_path)) == 2
    assert len(discover_files(tmp_path, recursive=True)) == 3


def test_discover_files_ignores_unsupported(tmp_path):
    (tmp_path / "a.wav").write_bytes(b"x")
    assert discover_files(tmp_path) == []


def test_discover_files_not_a_directory(tmp_path):
    with pytest.raises(NotADirectoryError):
        discover_files(tmp_path / "missing")


def test_cli_file_requires_metadata(capsys):
    code = main(["file", "song.mp3"])
    assert code == 2
    assert "no metadata" in capsys.readouterr().err.lower()


def test_cli_file_success(tmp_path):
    song = tmp_path / "s.mp3"
    song.write_bytes(b"x")
    with patch("metatune.cli.apply_metadata", return_value=True) as m:
        assert main(["file", str(song), "--artist", "A"]) == 0
    m.assert_called_once()


def test_cli_dir_no_files(tmp_path, capsys):
    assert main(["dir", str(tmp_path), "--artist", "A"]) == 0
    assert "No files" in capsys.readouterr().out


def test_cli_template_creates_file(tmp_path):
    out = tmp_path / "t.json"
    assert main(["template", "--output", str(out)]) == 0
    payload = json.loads(out.read_text())
    assert "defaults" in payload


def test_cli_show_missing_path():
    assert main(["show", "/definitely/not/here"]) == 1


def test_parser_has_all_subcommands(tmp_path):
    parser = build_parser()
    song = tmp_path / "s.mp3"
    song.write_bytes(b"x")
    assert parser.parse_args(["file", str(song), "--artist", "A"]).command == "file"
    assert parser.parse_args(["dir", str(tmp_path)]).command == "dir"
    assert parser.parse_args(["template"]).command == "template"
    assert parser.parse_args(["show", str(song)]).command == "show"
    assert parser.parse_args(["interactive"]).command == "interactive"
