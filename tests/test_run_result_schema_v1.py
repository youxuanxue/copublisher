import unittest

from copublisher.application.services.result_builder import RunResultBuilder
from copublisher.domain.error_codes import ErrorCode
from copublisher.domain.result import PlatformRunOutcome


class RunResultSchemaV1Tests(unittest.TestCase):
    def test_success_result_matches_schema_v1(self):
        builder = RunResultBuilder()
        result = builder.build(
            outcomes=[
                PlatformRunOutcome(
                    platform="wechat",
                    success=True,
                    message="https://example.com/post/1",
                    duration_ms=12,
                    idempotency_key="k1",
                )
            ],
            duration_ms=20,
            mode="legacy",
        ).as_dict()

        self.assertEqual(result["status"], "success")
        self.assertFalse(result["retryable"])
        self.assertFalse(result["manual_takeover_required"])
        self.assertIsNone(result["error"])
        self.assertIn("artifacts", result)
        self.assertEqual(result["artifacts"][0]["platform"], "wechat")
        self.assertEqual(result["metrics"]["schema_version"], "v1")
        self.assertEqual(result["metrics"]["mode"], "legacy")
        self.assertIn("platform_durations", result["metrics"])

    def test_partial_result_carries_error_and_retry_flags(self):
        builder = RunResultBuilder()
        result = builder.build(
            outcomes=[
                PlatformRunOutcome(
                    platform="wechat",
                    success=True,
                    message="ok",
                    duration_ms=11,
                ),
                PlatformRunOutcome(
                    platform="youtube",
                    success=False,
                    message="timeout",
                    error_code=ErrorCode.MP_PLATFORM_TIMEOUT,
                    retryable=True,
                    duration_ms=13,
                ),
            ],
            duration_ms=40,
            mode="legacy",
        ).as_dict()

        self.assertEqual(result["status"], "partial")
        self.assertTrue(result["retryable"])
        self.assertFalse(result["manual_takeover_required"])
        self.assertEqual(result["error"]["code"], "MP_PLATFORM_TIMEOUT")
        self.assertEqual(result["error"]["platform"], "youtube")
        self.assertEqual(result["metrics"]["schema_version"], "v1")

    def test_manual_takeover_flag_when_auth_required(self):
        builder = RunResultBuilder()
        result = builder.build(
            outcomes=[
                PlatformRunOutcome(
                    platform="wechat",
                    success=False,
                    message="auth required",
                    error_code=ErrorCode.MP_AUTH_REQUIRED,
                    retryable=False,
                    manual_takeover_required=True,
                    duration_ms=9,
                )
            ],
            duration_ms=9,
        ).as_dict()

        self.assertEqual(result["status"], "failed")
        self.assertFalse(result["retryable"])
        self.assertTrue(result["manual_takeover_required"])
        self.assertEqual(result["error"]["code"], "MP_AUTH_REQUIRED")


if __name__ == "__main__":
    unittest.main()

