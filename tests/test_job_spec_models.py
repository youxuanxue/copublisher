import json
import tempfile
import unittest
from pathlib import Path

from copublisher.domain.models import JobSpec


class JobSpecModelTests(unittest.TestCase):
    def test_platform_alias_both_expands(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            video = root / "demo.mp4"
            script = root / "script.json"
            video.write_bytes(b"fake")
            script.write_text(json.dumps({"wechat": {}}), encoding="utf-8")

            spec = JobSpec.from_payload(
                {
                    "job_id": "job_spec_01",
                    "mode": "legacy",
                    "platform": "both",
                    "video": str(video),
                    "script": str(script),
                },
                supported_platforms={"wechat", "youtube", "both"},
            )
            self.assertEqual(spec.platforms, ["wechat", "youtube"])

    def test_platforms_list_supported_validation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            video = root / "demo.mp4"
            script = root / "script.json"
            video.write_bytes(b"fake")
            script.write_text(json.dumps({"wechat": {}}), encoding="utf-8")

            with self.assertRaises(ValueError):
                JobSpec.from_payload(
                    {
                        "job_id": "job_spec_02",
                        "mode": "legacy",
                        "platforms": ["wechat", "unknown"],
                        "video": str(video),
                        "script": str(script),
                    },
                    supported_platforms={"wechat"},
                )


if __name__ == "__main__":
    unittest.main()

