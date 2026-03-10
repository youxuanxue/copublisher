import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from copublisher.__main__ import run_job_cli


class CliContractBackwardCompatTests(unittest.TestCase):
    def test_job_file_contract_v1_fields_exist(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            video = root / "demo.mp4"
            script = root / "script.json"
            job = root / "job.json"

            video.write_bytes(b"fake")
            script.write_text('{"wechat":{"title":"t","description":"d"}}', encoding="utf-8")
            job.write_text(
                json.dumps(
                    {
                        "job_id": "job_compat_1",
                        "mode": "legacy",
                        "platform": "wechat",
                        "video": str(video),
                        "script": str(script),
                        "dry_run": True,
                    }
                ),
                encoding="utf-8",
            )

            result = run_job_cli(
                Namespace(job_file=str(job), dry_run=False, result_file=None, json=True)
            )

            self.assertEqual(result["status"], "success")
            self.assertIn("retryable", result)
            self.assertIn("manual_takeover_required", result)
            self.assertIn("artifacts", result)
            self.assertIn("error", result)
            self.assertIn("metrics", result)
            self.assertEqual(result["metrics"]["schema_version"], "v1")

    def test_job_file_backward_compat_invalid_input_error_code(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            job = Path(tmp_dir) / "job.json"
            job.write_text(
                json.dumps(
                    {
                        "job_id": "job_compat_2",
                        "mode": "legacy",
                        "platform": "wechat",
                        "video": "/not-exists/video.mp4",
                        "script": "/not-exists/script.json",
                    }
                ),
                encoding="utf-8",
            )

            result = run_job_cli(
                Namespace(job_file=str(job), dry_run=False, result_file=None, json=True)
            )
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["error"]["code"], "MP_INPUT_INVALID")


if __name__ == "__main__":
    unittest.main()

