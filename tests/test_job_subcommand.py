import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class JobSubcommandTests(unittest.TestCase):
    def _run_cli(self, args: list[str]) -> subprocess.CompletedProcess:
        repo_root = Path(__file__).resolve().parents[1]
        env = os.environ.copy()
        env["PYTHONPATH"] = str(repo_root / "src")
        return subprocess.run(
            [sys.executable, "-m", "copublisher", *args],
            cwd=repo_root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_job_run_subcommand_with_job_file(self):
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
                        "job_id": "job_sub_01",
                        "mode": "legacy",
                        "platform": "wechat",
                        "video": str(video),
                        "script": str(script),
                        "dry_run": True,
                    }
                ),
                encoding="utf-8",
            )
            proc = self._run_cli(["job", "run", "--job-file", str(job), "--json"])
            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout.strip())
            self.assertEqual(payload["status"], "success")

    def test_job_run_subcommand_with_direct_args(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            video = root / "demo.mp4"
            script = root / "script.json"
            video.write_bytes(b"fake")
            script.write_text('{"wechat":{"title":"t","description":"d"}}', encoding="utf-8")
            proc = self._run_cli(
                [
                    "job",
                    "run",
                    "--job-id",
                    "job_sub_02",
                    "--platforms",
                    "wechat,youtube",
                    "--video",
                    str(video),
                    "--script",
                    str(script),
                    "--dry-run",
                    "--json",
                ]
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout.strip())
            self.assertEqual(payload["status"], "success")
            self.assertTrue(payload["metrics"]["dry_run"])

    def test_job_run_supports_blue_ocean_input_and_org_state_output(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            video = root / "demo.mp4"
            script = root / "script.json"
            action = root / "action.json"
            video.write_bytes(b"fake")
            script.write_text('{"wechat":{"title":"t","description":"d"}}', encoding="utf-8")
            action.write_text(
                json.dumps(
                    {
                        "action_id": "action_sub_01",
                        "job_id": "job_sub_03",
                        "platforms": ["wechat"],
                        "materials": {"video": str(video), "script": str(script)},
                    }
                ),
                encoding="utf-8",
            )
            proc = self._run_cli(
                [
                    "job",
                    "run",
                    "--blue-ocean-input",
                    str(action),
                    "--dry-run",
                    "--json",
                    "--org-state-json",
                    "--report-root",
                    str(root / "reports" / "org-runs"),
                ]
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout.strip())
            self.assertEqual(payload["org_state"], "SUCCESS")
            report_dir = root / "reports" / "org-runs" / "action_sub_01"
            self.assertTrue((report_dir / "summary.json").exists())


if __name__ == "__main__":
    unittest.main()

