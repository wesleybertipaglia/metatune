"""Command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from metatune import __version__
from metatune.metadata import (
    METADATA_FIELDS,
    Metadata,
    apply_metadata,
    apply_to_directory,
    read_metadata,
)
from metatune.template import generate_template, load_template
from metatune.utils import discover_files


def _add_metadata_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--title", default="", help="Track title")
    parser.add_argument("--artist", default="", help="Artist name (TPE1)")
    parser.add_argument("--album", default="", help="Album name (TALB)")
    parser.add_argument("--albumartist", default="", help="Album artist (TPE2)")
    parser.add_argument("--genre", default="", help="Genre (TCON)")
    parser.add_argument("--year", default="", help="Release year (TDRC)")
    parser.add_argument("--track", default="", help="Track number")
    parser.add_argument("--track-total", default="", help="Total number of tracks")
    parser.add_argument("--disc", default="", help="Disc number")
    parser.add_argument("--disc-total", default="", help="Total number of discs")
    parser.add_argument("--composer", default="", help="Composer (TCOM)")
    parser.add_argument("--comment", default="", help="Comment (COMM)")
    parser.add_argument("--cover", default="", help="Cover image path (.jpg/.png/.webp)")


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--from-template",
        dest="from_template",
        default=None,
        help="JSON template file (see 'template' command). CLI flags override it.",
    )
    parser.add_argument("--clear", action="store_true", help="Remove existing tags before writing")
    parser.add_argument("--dry-run", action="store_true", help="Validate without saving")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")


def _metadata_from_args(args: argparse.Namespace) -> dict:
    merged: dict[str, str] = {}
    if getattr(args, "from_template", None):
        defaults, _ = load_template(args.from_template)
        merged.update(defaults)
    for field in METADATA_FIELDS:
        cli_key = field.replace("_", "-") if field in ("track_total", "disc_total") else field
        attr = field if field not in ("track_total", "disc_total") else field
        # argparse converts --track-total -> args.track_total
        value = getattr(args, attr, "")
        if value not in (None, ""):
            merged[field] = str(value)
    # Silence unused-var lint about cli_key mapping; mapping is positional above.
    _ = cli_key
    return merged


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="metatune",
        description="MetaTune — batch MP3 (ID3) metadata editor: tag one song, a directory, or use a template.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    # Single file -----------------------------------------------------------
    p_file = sub.add_parser("file", help="Tag a single MP3 file")
    p_file.add_argument("path", help="Path to the .mp3 file")
    _add_metadata_args(p_file)
    _add_common_args(p_file)

    # Directory / batch ------------------------------------------------------
    p_dir = sub.add_parser("dir", help="Tag every MP3 in a directory (batch)")
    p_dir.add_argument("directory", help="Album directory")
    p_dir.add_argument("-r", "--recursive", action="store_true", help="Include subdirectories")
    p_dir.add_argument("--pattern", default="*.mp3", help="Glob pattern (default: *.mp3)")
    _add_metadata_args(p_dir)
    _add_common_args(p_dir)

    # Template ---------------------------------------------------------------
    p_tpl = sub.add_parser("template", help="Create a blank editable metadata template")
    p_tpl.add_argument("-o", "--output", default="metadata-template.json", help="Output path")
    p_tpl.add_argument("--force", action="store_true", help="Overwrite existing file")
    p_tpl.add_argument(
        "--apply-to",
        default=None,
        help="Optional: immediately apply this existing template to a file or directory",
    )
    p_tpl.add_argument("-r", "--recursive", action="store_true", help="Used with --apply-to dir: recurse")
    _add_metadata_args(p_tpl)
    _add_common_args(p_tpl)

    # Show -------------------------------------------------------------------
    p_show = sub.add_parser("show", help="Print current tags of a file or directory")
    p_show.add_argument("path", help="MP3 file or directory")
    p_show.add_argument("-r", "--recursive", action="store_true", help="Recurse when path is a directory")
    p_show.add_argument("--json", action="store_true", help="Output as JSON")

    # Interactive (legacy behaviour) -----------------------------------------
    sub.add_parser("interactive", help="Guided prompts (legacy main.py behaviour)")

    return parser


def _cmd_file(args: argparse.Namespace) -> int:
    metadata = _metadata_from_args(args)
    if not metadata:
        print("error: no metadata provided (flags and/or --from-template are all empty).", file=sys.stderr)
        return 2
    try:
        apply_metadata(args.path, metadata, clear_existing=args.clear, dry_run=args.dry_run)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 - surface mutagen errors cleanly
        print(f"error: could not tag '{args.path}': {exc}", file=sys.stderr)
        return 1
    suffix = " (dry run)" if args.dry_run else ""
    print(f"✓ {args.path}{suffix}")
    return 0


def _cmd_dir(args: argparse.Namespace) -> int:
    metadata = _metadata_from_args(args)
    per_file: dict[str, dict] = {}
    if getattr(args, "from_template", None):
        _, per_file = load_template(args.from_template)
    # CLI flags win over template defaults for every file.
    cli_overrides = {k: v for k, v in metadata.items()}
    try:
        files = discover_files(Path(args.directory), recursive=args.recursive, pattern=args.pattern)
    except NotADirectoryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if not files:
        print(f"No files matching '{args.pattern}' in {args.directory}.")
        return 0
    # Merge: template defaults <- per-file <- CLI flags.
    base_defaults, _ = (load_template(args.from_template) if args.from_template else ({}, {}))
    merged_per_file: dict[str, dict] = {}
    for f in files:
        entry = dict(base_defaults)
        entry.update(per_file.get(f.name, {}))
        entry.update(cli_overrides)
        merged_per_file[f.name] = entry
    if all(not v for v in merged_per_file.values()):
        print("error: no metadata provided (flags and/or --from-template are all empty).", file=sys.stderr)
        return 2
    result = apply_to_directory(
        args.directory,
        {},
        recursive=args.recursive,
        pattern=args.pattern,
        clear_existing=args.clear,
        dry_run=args.dry_run,
        per_file=merged_per_file,
    )
    for name in result["updated"]:
        print(f"✓ {name}" + (" (dry run)" if args.dry_run else ""))
    for name in result["failed"]:
        print(f"✗ {name}")
    for name in result["skipped"]:
        if args.verbose:
            print(f"- {name} (skipped: empty metadata)")
    print(f"\nDone. Updated {len(result['updated'])}, failed {len(result['failed'])}, skipped {len(result['skipped'])}.")
    return 1 if result["failed"] and not result["updated"] else 0


def _cmd_template(args: argparse.Namespace) -> int:
    inline = {f: getattr(args, f, "") for f in METADATA_FIELDS if getattr(args, f, "") not in (None, "")}
    if getattr(args, "apply_to", None):
        # Apply an existing template file directly.
        template_src = args.from_template or args.apply_to if Path(str(args.apply_to)).is_file() and not Path(str(args.apply_to)).is_dir() else args.from_template
        # Heuristic: if --apply-to points to an mp3/dir and --from-template given, use it;
        # if --apply-to points to a json file, treat it as the template.
        apply_target = args.apply_to
        maybe_template = Path(str(args.apply_to))
        if maybe_template.suffix.lower() == ".json" and maybe_template.is_file():
            template_src = str(maybe_template)
            print("error: --apply-to needs a file/dir target when it is itself a template.", file=sys.stderr)
            return 2
        if not template_src:
            print("error: --apply-to requires --from-template <template.json>.", file=sys.stderr)
            return 2
        target = Path(str(apply_target))
        fake_args = argparse.Namespace(
            from_template=template_src, clear=args.clear, dry_run=args.dry_run, verbose=False
        )
        for f in METADATA_FIELDS:
            setattr(fake_args, f, getattr(args, f, ""))
        if target.is_file():
            fake_args.path = str(target)
            return _cmd_file(fake_args)
        fake_args.directory = str(target)
        fake_args.recursive = args.recursive
        fake_args.pattern = "*.mp3"
        return _cmd_dir(fake_args)
    try:
        out = generate_template(args.output, force=args.force)
    except FileExistsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if inline:
        # Pre-fill the fresh template with CLI-provided values.
        import json as _json

        data = _json.loads(out.read_text(encoding="utf-8"))
        data["defaults"].update(inline)
        out.write_text(_json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Template created: {out}\nEdit it, then run e.g.:\n  metatune dir ./album --from-template {out}")
    return 0


def _cmd_show(args: argparse.Namespace) -> int:
    target = Path(args.path)
    files: list[Path] = []
    if target.is_file():
        files = [target]
    elif target.is_dir():
        files = discover_files(target, recursive=args.recursive)
    else:
        print(f"error: path not found: {args.path}", file=sys.stderr)
        return 1
    if not files:
        print("No MP3 files found.")
        return 0
    payload = {}
    for f in files:
        try:
            payload[str(f)] = read_metadata(f)
        except Exception as exc:  # noqa: BLE001
            payload[str(f)] = {"error": str(exc)}
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        for fname, tags in payload.items():
            print(f"== {fname} ==")
            if not tags:
                print("  (no tags)")
            for k, v in tags.items():
                print(f"  {k}: {v}")
    return 0


def _cmd_interactive() -> int:
    artist = album = ""
    if input("Will add artist name? (y/n): ").lower() == "y":
        artist = input("Artist name: ").strip()
    if input("Will add album name? (y/n): ").lower() == "y":
        album = input("Album name: ").strip()
    add_cover = input("Will add cover image? (y/n): ").lower() == "y"
    cover = ""
    if add_cover:
        cover = input("Cover image path: ").strip()
    album_dir = Path(input("Album directory: ").strip())
    metadata = {k: v for k, v in {"artist": artist, "album": album, "cover": cover}.items() if v}
    if not metadata:
        print("Nothing to do.")
        return 0
    args = argparse.Namespace(
        directory=str(album_dir), recursive=False, pattern="*.mp3",
        from_template=None, clear=False, dry_run=False, verbose=False,
        **{f: metadata.get(f, "") for f in METADATA_FIELDS},
    )
    return _cmd_dir(args)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "file":
        return _cmd_file(args)
    if args.command == "dir":
        return _cmd_dir(args)
    if args.command == "template":
        return _cmd_template(args)
    if args.command == "show":
        return _cmd_show(args)
    if args.command == "interactive":
        return _cmd_interactive()
    parser.print_help()
    return 2
