"""File discovery helpers."""

from __future__ import annotations

from pathlib import Path

SUPPORTED_EXTENSIONS = {".mp3"}


def is_supported(path: Path) -> bool:
    """Return True if the file has a supported audio extension."""
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def discover_files(
    directory: Path,
    recursive: bool = False,
    pattern: str = "*.mp3",
) -> list[Path]:
    """Find audio files inside *directory*.

    Args:
        directory: Base directory to search.
        recursive: If True, search subdirectories with rglob.
        pattern: Glob pattern (default ``*.mp3``).

    Returns:
        Sorted list of matching, supported files.
    """
    if not directory.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory}")
    globber = directory.rglob if recursive else directory.glob
    files = [p for p in globber(pattern) if p.is_file() and is_supported(p)]
    return sorted(files)
