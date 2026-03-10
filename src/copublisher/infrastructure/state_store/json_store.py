"""
Execution state store with atomic JSON persistence.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from copublisher.shared.io import atomic_write_json
from copublisher.shared.security import sanitize_identifier


class ExecutionStateStore:
    def __init__(self, root_dir: str | Path):
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def _state_path(self, job_id: str) -> Path:
        safe_job_id = sanitize_identifier(job_id, field_name="job_id")
        if not safe_job_id:
            raise ValueError("job_id 不能为空")
        return self.root_dir / f"{safe_job_id}.json"

    def load(self, job_id: str) -> dict[str, Any]:
        state_path = self._state_path(job_id)
        if not state_path.exists():
            return {
                "schema_version": "v1",
                "job_id": sanitize_identifier(job_id, field_name="job_id"),
                "platforms": {},
                "updated_at": None,
            }
        import json

        with state_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def save(self, job_id: str, state: dict[str, Any]) -> None:
        state = dict(state)
        state["schema_version"] = "v1"
        state["job_id"] = sanitize_identifier(job_id, field_name="job_id")
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        atomic_write_json(self._state_path(job_id), state, ensure_ascii=False)

    def get_platform_record(self, job_id: str, platform: str) -> dict[str, Any]:
        state = self.load(job_id)
        return dict(state.get("platforms", {}).get(platform, {}))

    def upsert_platform_record(self, job_id: str, platform: str, record: dict[str, Any]) -> None:
        state = self.load(job_id)
        platforms = dict(state.get("platforms", {}))
        platforms[platform] = record
        state["platforms"] = platforms
        self.save(job_id, state)

