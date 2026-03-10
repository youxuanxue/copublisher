"""
Run result schema v1 (stable contract).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from copublisher.domain.error_codes import ErrorCode

RunStatus = Literal["success", "failed", "partial"]


@dataclass
class Artifact:
    type: str
    path: str
    platform: str

    def as_dict(self) -> dict[str, str]:
        return {"type": self.type, "path": self.path, "platform": self.platform}


@dataclass
class ErrorDetail:
    code: ErrorCode
    message: str
    platform: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code.value,
            "message": self.message,
            "platform": self.platform,
            "details": self.details,
        }


@dataclass
class RunMetrics:
    schema_version: str = "v1"
    duration_ms: int = 0
    retries: int = 0
    platform_durations: dict[str, int] = field(default_factory=dict)
    platform_retries: dict[str, int] = field(default_factory=dict)
    mode: str = "job"
    dry_run: bool = False
    trace_id: str | None = None
    job_id: str | None = None
    platform_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    idempotency_keys: dict[str, str] = field(default_factory=dict)
    skipped_platforms: list[str] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "duration_ms": self.duration_ms,
            "retries": self.retries,
            "platform_durations": self.platform_durations,
            "platform_retries": self.platform_retries,
            "mode": self.mode,
            "dry_run": self.dry_run,
            "trace_id": self.trace_id,
            "job_id": self.job_id,
            "platform_results": self.platform_results,
            "idempotency_keys": self.idempotency_keys,
            "skipped_platforms": self.skipped_platforms,
            "events": self.events,
        }


@dataclass
class RunResult:
    status: RunStatus
    retryable: bool
    manual_takeover_required: bool
    artifacts: list[Artifact] = field(default_factory=list)
    error: ErrorDetail | None = None
    metrics: RunMetrics = field(default_factory=RunMetrics)

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "retryable": self.retryable,
            "manual_takeover_required": self.manual_takeover_required,
            "artifacts": [a.as_dict() for a in self.artifacts],
            "error": self.error.as_dict() if self.error else None,
            "metrics": self.metrics.as_dict(),
        }


@dataclass
class PlatformRunOutcome:
    platform: str
    success: bool
    message: str
    error_code: ErrorCode | None = None
    retryable: bool = False
    manual_takeover_required: bool = False
    duration_ms: int = 0
    retries: int = 0
    artifact_path: str | None = None
    skipped: bool = False
    idempotency_key: str | None = None

