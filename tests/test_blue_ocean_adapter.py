import json
import tempfile
import unittest
from pathlib import Path

from copublisher.application.services.blue_ocean_adapter import (
    build_job_payload_from_action,
    load_blue_ocean_request,
    map_run_result_to_org_state,
)


class BlueOceanAdapterTests(unittest.TestCase):
    def test_build_job_payload_from_action_success(self):
        action = {
            "action_id": "action_01",
            "job_id": "job_01",
            "platforms": ["wechat", "youtube"],
            "materials": {"video": "/tmp/v.mp4", "script": "/tmp/s.json"},
            "account": "team_01",
            "idempotency_key": "idem_01",
        }
        payload = build_job_payload_from_action(action)
        self.assertEqual(payload["action_id"], "action_01")
        self.assertEqual(payload["job_id"], "job_01")
        self.assertEqual(payload["platform"], "wechat,youtube")
        self.assertEqual(payload["account"], "team_01")

    def test_build_job_payload_rejects_unsafe_identifier(self):
        with self.assertRaises(ValueError):
            build_job_payload_from_action(
                {
                    "action_id": "action_01",
                    "job_id": "job_01",
                    "platform": "wechat",
                    "materials": {"video": "/tmp/v.mp4", "script": "/tmp/s.json"},
                    "account": "../evil",
                }
            )

    def test_map_run_result_to_org_state(self):
        success = map_run_result_to_org_state(
            {
                "status": "success",
                "retryable": False,
                "manual_takeover_required": False,
                "metrics": {"platform_results": {"wechat": {"success": True}}},
            }
        )
        self.assertEqual(success["org_state"], "SUCCESS")
        self.assertEqual(success["retry_platforms"], [])

        retry = map_run_result_to_org_state(
            {
                "status": "failed",
                "retryable": True,
                "manual_takeover_required": False,
                "metrics": {
                    "platform_results": {
                        "youtube": {
                            "success": False,
                            "retryable": True,
                            "manual_takeover_required": False,
                        }
                    }
                },
            }
        )
        self.assertEqual(retry["org_state"], "RETRY_PENDING")
        self.assertEqual(retry["retry_platforms"], ["youtube"])

        manual = map_run_result_to_org_state(
            {
                "status": "failed",
                "retryable": False,
                "manual_takeover_required": True,
                "metrics": {
                    "platform_results": {
                        "wechat": {
                            "success": False,
                            "retryable": False,
                            "manual_takeover_required": True,
                        }
                    }
                },
            }
        )
        self.assertEqual(manual["org_state"], "MANUAL_TAKEOVER")
        self.assertEqual(manual["manual_takeover_platforms"], ["wechat"])

    def test_load_blue_ocean_request_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            p = Path(tmp_dir) / "action.json"
            p.write_text(json.dumps({"job_id": "j"}), encoding="utf-8")
            payload = load_blue_ocean_request(p)
            self.assertEqual(payload["job_id"], "j")


if __name__ == "__main__":
    unittest.main()

