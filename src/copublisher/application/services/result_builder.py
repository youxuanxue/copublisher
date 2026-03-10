"""
Build stable RunResult v1 objects from per-platform outcomes.
"""

from __future__ import annotations

from typing import Iterable

from copublisher.domain.error_codes import ErrorCode
from copublisher.domain.result import (
    Artifact,
    ErrorDetail,
    PlatformRunOutcome,
    RunMetrics,
    RunResult,
)


class RunResultBuilder:
    def build(
        self,
        *,
        outcomes: Iterable[PlatformRunOutcome],
        duration_ms: int,
        mode: str = "job",
        dry_run: bool = False,
        trace_id: str | None = None,
        job_id: str | None = None,
        events: list[dict] | None = None,
    ) -> RunResult:
        all_outcomes = list(outcomes)
        failures = [o for o in all_outcomes if not o.success]
        successes = [o for o in all_outcomes if o.success]

        if failures and successes:
            status = "partial"
        elif failures:
            status = "failed"
        else:
            status = "success"

        retryable = any(o.retryable for o in failures)
        manual_takeover_required = any(o.manual_takeover_required for o in failures)

        first_failure = failures[0] if failures else None
        error = None
        if first_failure:
            error = ErrorDetail(
                code=first_failure.error_code or ErrorCode.MP_PLATFORM_ERROR,
                message=first_failure.message,
                platform=first_failure.platform,
                details={},
            )

        artifacts = [
            Artifact(type="url", path=o.message, platform=o.platform)
            for o in all_outcomes
            if o.success and o.message and o.message.startswith("http")
        ]
        artifacts.extend(
            Artifact(type="file", path=o.artifact_path, platform=o.platform)
            for o in all_outcomes
            if o.artifact_path
        )

        metrics = RunMetrics(
            schema_version="v1",
            duration_ms=duration_ms,
            retries=sum(o.retries for o in all_outcomes),
            platform_durations={o.platform: o.duration_ms for o in all_outcomes},
            platform_retries={o.platform: o.retries for o in all_outcomes},
            mode=mode,
            dry_run=dry_run,
            trace_id=trace_id,
            job_id=job_id,
            platform_results={
                o.platform: {
                    "success": o.success,
                    "message": o.message,
                    "error_code": o.error_code.value if o.error_code else None,
                    "retryable": o.retryable,
                    "manual_takeover_required": o.manual_takeover_required,
                    "duration_ms": o.duration_ms,
                    "retries": o.retries,
                    "skipped": o.skipped,
                }
                for o in all_outcomes
            },
            idempotency_keys={
                o.platform: o.idempotency_key
                for o in all_outcomes
                if o.idempotency_key is not None
            },
            skipped_platforms=[o.platform for o in all_outcomes if o.skipped],
            events=list(events or []),
        )

        return RunResult(
            status=status,
            retryable=retryable,
            manual_takeover_required=manual_takeover_required,
            artifacts=artifacts,
            error=error,
            metrics=metrics,
        )

