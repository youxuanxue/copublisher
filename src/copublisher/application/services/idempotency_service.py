"""
Idempotency key generation and execution-state decisions.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from copublisher.infrastructure.state_store.json_store import ExecutionStateStore


def _hash_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 64)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


class IdempotencyService:
    def __init__(self, state_store: ExecutionStateStore):
        self.state_store = state_store

    def compute_content_hash(self, *, video_path: Path, script_data: dict[str, Any]) -> str:
        hasher = hashlib.sha256()
        hasher.update(_hash_file(video_path).encode("utf-8"))
        normalized_script = json.dumps(script_data, sort_keys=True, ensure_ascii=False)
        hasher.update(normalized_script.encode("utf-8"))
        return hasher.hexdigest()

    def build_key(
        self,
        *,
        job_id: str,
        platform: str,
        video_path: Path,
        script_data: dict[str, Any],
    ) -> str:
        content_hash = self.compute_content_hash(video_path=video_path, script_data=script_data)
        base = f"{job_id}:{platform}:{content_hash}"
        return hashlib.sha256(base.encode("utf-8")).hexdigest()

    def should_skip(self, *, job_id: str, platform: str, idempotency_key: str) -> bool:
        record = self.state_store.get_platform_record(job_id, platform)
        return bool(
            record
            and record.get("status") == "success"
            and record.get("idempotency_key") == idempotency_key
        )

    def get_retry_count(self, *, job_id: str, platform: str) -> int:
        record = self.state_store.get_platform_record(job_id, platform)
        return int(record.get("retries", 0))

    def mark_success(self, *, job_id: str, platform: str, idempotency_key: str, duration_ms: int) -> None:
        current_retry = self.get_retry_count(job_id=job_id, platform=platform)
        self.state_store.upsert_platform_record(
            job_id,
            platform,
            {
                "status": "success",
                "idempotency_key": idempotency_key,
                "retries": current_retry,
                "last_error": None,
                "duration_ms": duration_ms,
            },
        )

    def mark_failure(
        self,
        *,
        job_id: str,
        platform: str,
        idempotency_key: str,
        error: dict[str, Any],
        duration_ms: int,
    ) -> int:
        retries = self.get_retry_count(job_id=job_id, platform=platform) + 1
        self.state_store.upsert_platform_record(
            job_id,
            platform,
            {
                "status": "failed",
                "idempotency_key": idempotency_key,
                "retries": retries,
                "last_error": error,
                "duration_ms": duration_ms,
            },
        )
        return retries

