import json
import tempfile
import unittest
from pathlib import Path

from copublisher.application.services.idempotency_service import IdempotencyService
from copublisher.application.usecases.run_job import RunJobInput, RunJobUseCase
from copublisher.domain.error_codes import ErrorCode, get_policy
from copublisher.domain.result import PlatformRunOutcome
from copublisher.infrastructure.registry import PublisherRegistry
from copublisher.infrastructure.state_store.json_store import ExecutionStateStore


class _AlwaysSuccessPublisher:
    def __init__(self, platform: str, calls: dict[str, int]):
        self.platform = platform
        self.calls = calls

    def publish(self, *, video_path: Path, script_data: dict, privacy: str, account: str | None):
        del video_path, script_data, privacy, account
        self.calls[self.platform] = self.calls.get(self.platform, 0) + 1
        return PlatformRunOutcome(
            platform=self.platform,
            success=True,
            message="ok",
            duration_ms=1,
        )


class _FailOncePublisher:
    def __init__(self, platform: str, calls: dict[str, int]):
        self.platform = platform
        self.calls = calls

    def publish(self, *, video_path: Path, script_data: dict, privacy: str, account: str | None):
        del video_path, script_data, privacy, account
        current = self.calls.get(self.platform, 0)
        self.calls[self.platform] = current + 1
        if current == 0:
            policy = get_policy(ErrorCode.MP_PLATFORM_TIMEOUT)
            return PlatformRunOutcome(
                platform=self.platform,
                success=False,
                message="first attempt timeout",
                error_code=ErrorCode.MP_PLATFORM_TIMEOUT,
                retryable=policy.retryable,
                manual_takeover_required=policy.manual_takeover_required,
                duration_ms=2,
            )
        return PlatformRunOutcome(
            platform=self.platform,
            success=True,
            message="recovered",
            duration_ms=2,
        )


class IdempotencyServiceTests(unittest.TestCase):
    def test_idempotency_key_is_stable_for_same_payload(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            video = root / "demo.mp4"
            video.write_bytes(b"video")
            script_data = {"wechat": {"title": "t"}}

            service = IdempotencyService(ExecutionStateStore(root / "state"))
            key1 = service.build_key(
                job_id="job_01",
                platform="wechat",
                video_path=video,
                script_data=script_data,
            )
            key2 = service.build_key(
                job_id="job_01",
                platform="wechat",
                video_path=video,
                script_data=script_data,
            )
            self.assertEqual(key1, key2)

    def test_partial_retry_runs_only_failed_platform(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            state_store = ExecutionStateStore(root / "state")
            idempotency = IdempotencyService(state_store)
            calls: dict[str, int] = {}

            registry = PublisherRegistry()
            registry.register("wechat", factory=lambda: _FailOncePublisher("wechat", calls))
            registry.register("youtube", factory=lambda: _AlwaysSuccessPublisher("youtube", calls))

            usecase = RunJobUseCase(registry=registry, idempotency_service=idempotency)

            video = root / "demo.mp4"
            script = root / "script.json"
            job = root / "job.json"
            video.write_bytes(b"video")
            script.write_text(json.dumps({"wechat": {}, "youtube": {}}), encoding="utf-8")
            job.write_text(
                json.dumps(
                    {
                        "job_id": "job_01",
                        "mode": "legacy",
                        "platform": "both",
                        "video": str(video),
                        "script": str(script),
                    }
                ),
                encoding="utf-8",
            )

            first = usecase.execute(RunJobInput(job_file=str(job)))
            self.assertEqual(first["status"], "partial")
            self.assertEqual(calls["wechat"], 1)
            self.assertEqual(calls["youtube"], 1)

            second = usecase.execute(RunJobInput(job_file=str(job)))
            self.assertEqual(second["status"], "success")
            self.assertEqual(calls["wechat"], 2)
            self.assertEqual(
                calls["youtube"],
                1,
                "youtube should be skipped on retry after prior success",
            )
            self.assertIn("youtube", second["metrics"]["skipped_platforms"])


if __name__ == "__main__":
    unittest.main()

