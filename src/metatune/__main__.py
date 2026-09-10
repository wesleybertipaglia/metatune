"""Allow ``python -m metatune`` execution."""

from metatune.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
