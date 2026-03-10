import json
import tempfile
import unittest
from pathlib import Path

from copublisher.application.services.org_run_reporter import OrgRunReporter


class OrgRunReporterTests(unittest.TestCase):
    def test_write_org_run_reports_with_summary(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            reporter = OrgRunReporter(root_dir=Path(tmp_dir) / "reports" / "org-runs")
            run_result = {
                "status": "partial",
                "retryable": True,
                "manual_takeover_required": False,
                "metrics": {
                    "trace_id": "trace_01",
                    "job_id": "job_01",
                    "platform_results": {
                        "wechat": {
                            "success": True,
                            "retryable": False,
                            "manual_takeover_required": False,
                        },
                        "youtube": {
                            "success": False,
                            "retryable": True,
                            "manual_takeover_required": False,
                        },
                    },
                },
            }
            org_state = {
                "org_state": "RETRY_PENDING",
                "retry_platforms": ["youtube"],
                "manual_takeover_platforms": [],
            }
            path = reporter.write(
                org_run_id="run_01",
                action_payload={"action_id": "run_01"},
                job_payload={
                    "job_id": "job_01",
                    "video": "/tmp/v.mp4",
                    "script": "/tmp/s.json",
                },
                run_result=run_result,
                org_state=org_state,
            )
            self.assertTrue(path.exists())
            summary = json.loads((path / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["org_run_id"], "run_01")
            self.assertEqual(summary["org_state"], "RETRY_PENDING")
            self.assertIn("youtube", summary["retry_platforms"])
            self.assertIn("--platforms youtube", summary["retry_entry_hint"])

    def test_write_rejects_unsafe_org_run_id(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            reporter = OrgRunReporter(root_dir=Path(tmp_dir))
            with self.assertRaises(ValueError):
                reporter.write(
                    org_run_id="../bad",
                    action_payload=None,
                    job_payload={},
                    run_result={},
                    org_state={},
                )


if __name__ == "__main__":
    unittest.main()

