"""
Atomic file write helpers for state/config outputs.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def atomic_write_text(
    path: str | Path,
    content: str,
    encoding: str = "utf-8",
    mode: int | None = None,
) -> None:
    """Write text atomically via temp file + rename.

    Args:
        path: Target file path.
        content: Text to write.
        encoding: Text encoding (default utf-8).
        mode: If set, ``os.chmod(target, mode)`` after rename.
              Use ``0o600`` for credential/token files.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=str(target.parent),
        text=True,
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding=encoding) as tmp_file:
            tmp_file.write(content)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
        os.replace(tmp_path, target)
        if mode is not None:
            os.chmod(target, mode)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def read_json_with_size_limit(
    path: Path, max_size: int = 1024 * 1024, label: str = "文件"
) -> dict[str, Any]:
    """读取 JSON 文件，限制大小防止 DoS。"""
    size = path.stat().st_size
    if size > max_size:
        raise ValueError(f"{label}过大: {size} bytes (上限 {max_size} bytes): {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write_json(
    path: str | Path,
    payload: Any,
    ensure_ascii: bool = False,
    mode: int | None = None,
) -> None:
    """Serialize JSON and write atomically.

    Args:
        path: Target file path.
        payload: JSON-serializable object.
        ensure_ascii: Passed to ``json.dumps``.
        mode: Forwarded to ``atomic_write_text`` (e.g. ``0o600``).
    """
    text = json.dumps(payload, ensure_ascii=ensure_ascii, indent=2)
    atomic_write_text(path, text, mode=mode)
