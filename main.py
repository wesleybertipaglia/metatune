"""Backward-compatible entry point for MetaTune.

The project is now modular (see the ``metatune`` package).
Running ``python main.py`` starts the legacy interactive prompt,
while all new features live in the CLI::

    python -m metatune --help
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from metatune.cli import main


def _interactive_legacy() -> int:
    # Preserve the original behaviour when invoked without arguments:
    # go straight to the guided prompts.
    if len(sys.argv) == 1:
        return main(["interactive"])
    # Otherwise forward args to the new CLI (e.g. `python main.py dir ...`).
    return main(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(_interactive_legacy())
