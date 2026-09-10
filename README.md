# MetaTune

*Tune your tags.* Batch MP3 (ID3) metadata editor with single-file tagging, directory batch mode, and editable JSON templates.

## Features

- Tag a **single MP3** (`file` command)
- Tag a whole **directory in batch**, optionally recursive (`dir` command)
- Create and reuse an **editable JSON metadata template** (`template` command + `--from-template`)
- Per-track overrides inside templates (different title/track per file)
- Inspect current tags (`show` command, text or JSON)
- Embed cover art (JPEG / PNG / WebP)
- `--dry-run`, `--clear`, `--verbose` safety flags
- Legacy guided prompts (`interactive` command / `python main.py`)

Supported fields: `title`, `artist`, `album`, `albumartist`, `genre`, `year`,
`track` / `track_total`, `disc` / `disc_total`, `composer`, `comment`, `cover`.

## Requirements

- Python 3.9+
- [mutagen](https://mutagen.readthedocs.io/)

## Installation

```bash
# venv
python -m venv .venv
source .venv/bin/activate


# install
make install
# or
pip install -r requirements.txt

# run tests
make test
```

The package uses the `src/` layout (`src/metatune/`). After `make dev`
the `metatune` command and `python -m metatune` work from anywhere;
`make` targets also export `PYTHONPATH=src`, so they run without installing.

## Quick start

```bash
# 1. See all commands
python -m metatune --help

# 2. Tag a single song
python -m metatune file ./song.mp3 \
  --artist "Pink Floyd" --album "The Wall" \
  --title "Time" --track 4 --track-total 26 --genre "Progressive Rock"

# 3. Tag a whole album directory
python -m metatune dir ./my-album \
  --artist "Pink Floyd" --album "The Wall" --genre "Rock"

# 4. Include subdirectories
python -m metatune dir ./music --recursive --artist "Various" --genre "Rock"

# 5. Preview without writing anything
python -m metatune dir ./my-album --artist "X" --dry-run
```

## Templates

Templates are the recommended way to tag consistently and review changes.

```bash
# Create a blank template
python -m metatune template --output metadata-template.json

# Or via make
make template-example
```

Edit the file in any editor:

```json
{
  "defaults": {
    "artist": "Pink Floyd",
    "album": "The Wall",
    "genre": "Progressive Rock",
    "year": "1979",
    "cover": "./cover.jpg"
  },
  "tracks": {
    "01-in-the-flesh.mp3": { "title": "In The Flesh?", "track": "1" },
    "02-the-thin-ice.mp3": { "title": "The Thin Ice", "track": "2" }
  }
}
```

Then apply it:

```bash
# Flat template applied to one file
python -m metatune file ./song.mp3 --from-template metadata-template.json

# Structured template applied to a directory
python -m metatune dir ./my-album --from-template metadata-template.json

# CLI flags override template values
python -m metatune dir ./my-album \
  --from-template metadata-template.json --genre "Rock" --year 2011
```

A ready-to-edit example lives in [`examples/metadata-template.json`](examples/metadata-template.json).
Two shapes are accepted: a flat object (`{"artist": ...}`) or the
structured `{"defaults": {...}, "tracks": {...}}` form above.

## Inspecting tags

```bash
python -m metatune show ./song.mp3
python -m metatune show ./my-album --recursive
python -m metatune show ./song.mp3 --json
```

## CLI reference

| Command | Purpose | Key options |
|---|---|---|
| `file PATH` | Tag one MP3 | metadata flags, `--from-template`, `--clear`, `--dry-run` |
| `dir DIR` | Tag all MP3s in a directory | `--recursive`, `--pattern`, metadata flags, `--from-template`, `--clear`, `--dry-run` |
| `template` | Create a blank template | `--output`, `--force` |
| `show PATH` | Print existing tags | `--recursive`, `--json` |
| `interactive` | Guided prompts (legacy) | — |

Metadata flags (usable with `file` / `dir`):
`--title`, `--artist`, `--album`, `--albumartist`, `--genre`, `--year`,
`--track`, `--track-total`, `--disc`, `--disc-total`,
`--composer`, `--comment`, `--cover`.

## Project structure

```text
metatune/
├── src/metatune/
│   ├── __init__.py      # version
│   ├── __main__.py      # `python -m metatune`
│   ├── cli.py           # argparse commands
│   ├── metadata.py      # ID3 read/write (mutagen)
│   ├── template.py      # JSON template create/load
│   └── utils.py         # file discovery
├── tests/
│   ├── test_metadata.py
│   ├── test_template.py
│   └── test_cli.py
├── examples/
│   └── metadata-template.json
├── main.py              # legacy shim -> interactive mode
├── Makefile
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Development

```bash
make test           # run pytest
make test-verbose   # verbose tests
make lint           # compileall + ruff (if installed)
make format         # ruff format (if installed)
make clean          # remove caches/artifacts
make help           # list all targets
```

## License

MIT — see [LICENSE](LICENSE).
