"""
Shared configuration helpers.
"""

from __future__ import annotations

from pathlib import Path


def find_config_file(config_path: str) -> Path:
    """
    Locate a config file by searching multiple candidate directories.

    Checks (in order):
      1. The literal path
      2. ``cwd / config_path``
      3. ``cwd.parent / config_path``

    Returns the first existing path, or falls back to ``Path(config_path)``
    so callers get a clear ``FileNotFoundError`` later.
    """
    candidates = [
        Path(config_path),
        Path.cwd() / config_path,
        Path.cwd().parent / config_path,
    ]
    for path in candidates:
        if path.exists():
            return path
    return Path(config_path)
