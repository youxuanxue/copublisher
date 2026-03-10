"""
RunJob use case orchestrating publishers via registry + ports.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from copublisher.application.services.idempotency_service import IdempotencyService
from copublisher.application.services.result_builder import RunResultBuilder
from copublisher.domain.error_codes import (
    ErrorCode,
    build_error_payload,
    get_policy,
    map_exception_to_error_code,
)
from copublisher.domain.models import JobSpec
from copublisher.domain.result import PlatformRunOutcome
from copublisher.infrastructure.registry import PublisherRegistry

MAX_JOB_FILE_BYTES = 1024 * 1024
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RunJobInput:
    job_file: str
    cli_dry_run: bool = False


class RunJobUseCase:
    def __init__(
        self,
        *,
        registry: PublisherRegistry,
        idempotency_service: IdempotencyService,
        result_builder: RunResultBuilder | None = None,
    ):
        self.registry = registry
        self.idempotency_service = idempotency_service
        self.result_builder = result_builder or RunResultBuilder()

    def execute(self, job_input: RunJobInput) -> dict[str, Any]:
        job_path = Path(job_input.job_file)
        started = time.perf_counter()
        if not job_path.exists():
            return self._error_result(
                code=ErrorCode.MP_INPUT_INVALID,
                message=f"job 文件不存在: {job_path}",
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
        try:
            payload = self._load_json_with_limit(job_path)
        except ValueError as exc:
            return self._error_result(
                code=ErrorCode.MP_INPUT_INVALID,
                message=str(exc),
                duration_ms=int((time.perf_counter() - started) * 1000),
            )

        return self.execute_payload(payload, cli_dry_run=job_input.cli_dry_run)

    def execute_payload(self, payload: Mapping[str, Any], cli_dry_run: bool = False) -> dict[str, Any]:
        started = time.perf_counter()
        events: list[dict[str, Any]] = []
        trace_id = str(payload.get("trace_id") or uuid4())
        try:
            supported = set(self.registry.list_platforms()) | {
                "both",
                "all",
                "all-articles",
                "all-videos",
            }
            spec = JobSpec.from_payload(
                dict(payload),
                cli_dry_run=cli_dry_run,
                supported_platforms=supported,
            )
            script_data = spec.load_script_data()

            if spec.dry_run:
                result = self.result_builder.build(
                    outcomes=[
                        PlatformRunOutcome(
                            platform=p,
                            success=True,
                            message="dry-run",
                            skipped=True,
                        )
                        for p in spec.platforms
                    ],
                    duration_ms=int((time.perf_counter() - started) * 1000),
                    mode=spec.mode,
                    dry_run=True,
                    trace_id=trace_id,
                    job_id=spec.job_id,
                    events=events,
                )
                result.retryable = False
                result.manual_takeover_required = False
                return result.as_dict()

            outcomes: list[PlatformRunOutcome] = []
            for platform in spec.platforms:
                attempt = self.idempotency_service.get_retry_count(
                    job_id=spec.job_id, platform=platform
                ) + 1
                started_platform = time.perf_counter()
                events.append(
                    self._event(
                        trace_id=trace_id,
                        job_id=spec.job_id,
                        platform=platform,
                        attempt=attempt,
                        stage="start",
                        duration_ms=0,
                    )
                )
                key = self.idempotency_service.build_key(
                    job_id=spec.job_id,
                    platform=platform,
                    video_path=spec.video_path,
                    script_data=script_data,
                )
                if self.idempotency_service.should_skip(
                    job_id=spec.job_id,
                    platform=platform,
                    idempotency_key=key,
                ):
                    outcomes.append(
                        PlatformRunOutcome(
                            platform=platform,
                            success=True,
                            message="skipped (already successful)",
                            skipped=True,
                            retries=self.idempotency_service.get_retry_count(
                                job_id=spec.job_id, platform=platform
                            ),
                            idempotency_key=key,
                        )
                    )
                    events.append(
                        self._event(
                            trace_id=trace_id,
                            job_id=spec.job_id,
                            platform=platform,
                            attempt=attempt,
                            stage="skipped",
                            duration_ms=int((time.perf_counter() - started_platform) * 1000),
                        )
                    )
                    continue

                publisher = self.registry.get(platform)
                platform_outcome = publisher.publish(
                    video_path=spec.video_path,
                    script_data=script_data,
                    privacy=spec.privacy,
                    account=spec.account,
                )
                platform_outcome.idempotency_key = key
                if platform_outcome.success:
                    self.idempotency_service.mark_success(
                        job_id=spec.job_id,
                        platform=platform,
                        idempotency_key=key,
                        duration_ms=platform_outcome.duration_ms,
                    )
                else:
                    retries = self.idempotency_service.mark_failure(
                        job_id=spec.job_id,
                        platform=platform,
                        idempotency_key=key,
                        error=build_error_payload(
                            code=platform_outcome.error_code or ErrorCode.MP_PLATFORM_ERROR,
                            message=platform_outcome.message,
                            platform=platform,
                        ),
                        duration_ms=platform_outcome.duration_ms,
                    )
                    platform_outcome.retries = retries
                outcomes.append(platform_outcome)
                events.append(
                    self._event(
                        trace_id=trace_id,
                        job_id=spec.job_id,
                        platform=platform,
                        attempt=attempt,
                        stage="finished",
                        duration_ms=platform_outcome.duration_ms,
                    )
                )

            result = self.result_builder.build(
                outcomes=outcomes,
                duration_ms=int((time.perf_counter() - started) * 1000),
                mode=spec.mode,
                trace_id=trace_id,
                job_id=spec.job_id,
                events=events,
            )
            return result.as_dict()
        except ValueError as exc:
            return self._error_result(
                code=ErrorCode.MP_INPUT_INVALID,
                message=str(exc),
                duration_ms=int((time.perf_counter() - started) * 1000),
                trace_id=trace_id,
                events=events,
            )
        except KeyError as exc:
            return self._error_result(
                code=ErrorCode.MP_INPUT_INVALID,
                message=str(exc),
                duration_ms=int((time.perf_counter() - started) * 1000),
                trace_id=trace_id,
                events=events,
            )
        except Exception as exc:
            code = map_exception_to_error_code(exc)
            return self._error_result(
                code=code,
                message=str(exc),
                duration_ms=int((time.perf_counter() - started) * 1000),
                trace_id=trace_id,
                events=events,
            )

    def _error_result(
        self,
        *,
        code: ErrorCode,
        message: str,
        duration_ms: int,
        trace_id: str | None = None,
        events: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        policy = get_policy(code)
        result = self.result_builder.build(
            outcomes=[
                PlatformRunOutcome(
                    platform="job",
                    success=False,
                    message=message,
                    error_code=code,
                    retryable=policy.retryable,
                    manual_takeover_required=policy.manual_takeover_required,
                    duration_ms=duration_ms,
                )
            ],
            duration_ms=duration_ms,
            mode="job",
            trace_id=trace_id,
            events=events or [],
        )
        return result.as_dict()

    def _load_json_with_limit(self, path: Path) -> dict[str, Any]:
        size = path.stat().st_size
        if size > MAX_JOB_FILE_BYTES:
            raise ValueError(f"job 文件过大: {size} bytes (max {MAX_JOB_FILE_BYTES})")
        data = path.read_bytes()
        try:
            payload = json.loads(data.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"job JSON 格式错误: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValueError("job JSON 顶层必须是对象")
        return payload

    def _event(
        self,
        *,
        trace_id: str,
        job_id: str,
        platform: str,
        attempt: int,
        stage: str,
        duration_ms: int,
    ) -> dict[str, Any]:
        event = {
            "trace_id": trace_id,
            "job_id": job_id,
            "platform": platform,
            "attempt": attempt,
            "stage": stage,
            "duration_ms": duration_ms,
        }
        logger.info(
            "run_job_event",
            extra={"run_job_event": event},
        )
        return event

