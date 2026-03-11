import unittest
from pathlib import Path

from copublisher.application.usecases.publish_content import PublishContentUseCase


class _FakeExecutor:
    def __init__(self):
        self.calls: list[str] = []

    def close_wechat_browser(self) -> bool:
        self.calls.append("close")
        return False

    def load_episode_overview(self, *, episode_path: Path) -> tuple[str, str]:
        return "summary", "preview"

    def run_list_drafts(self, *, batch_dirs: list, account=None) -> tuple[str, list, Path | None]:
        return "", [], None

    def run_wechat_batch(self, *, batch_dir: Path, pairs: list, account=None) -> list:
        return [(True, "ok") for _ in pairs]

    def run_legacy_script(self, *, video_path: Path, script_data: dict, platform: str, privacy: str, account=None, keep_wechat_browser_open: bool = False):
        del video_path, script_data, privacy, account, keep_wechat_browser_open
        if platform == "both":
            self.calls.extend(["wechat", "youtube"])
            return {"wechat": (True, "wechat-ok"), "youtube": (True, "youtube-ok")}
        self.calls.append(platform)
        return {platform: (True, f"{platform}-ok")}

    def run_episode_adapter(self, *, episode_path: Path, platforms: list[str], video_path: Path | None, privacy: str, account=None, keep_wechat_browser_open: bool = False):
        del episode_path, video_path, privacy, account, keep_wechat_browser_open
        self.calls.append("episode")
        return {p: (True, f"{p}-ok") for p in platforms}


class PublishContentUseCaseTests(unittest.TestCase):
    def test_run_legacy_script_dispatches_both_platforms(self):
        fake = _FakeExecutor()
        usecase = PublishContentUseCase(executor=fake)
        result = usecase.run_legacy_script(
            video_path=Path("/tmp/fake.mp4"),
            script_data={},
            platform="both",
            privacy="private",
            account=None,
            keep_wechat_browser_open=False,
        )
        self.assertEqual(fake.calls, ["wechat", "youtube"])
        self.assertTrue(result["wechat"][0])
        self.assertTrue(result["youtube"][0])

    def test_run_legacy_script_dispatches_single_platform(self):
        fake = _FakeExecutor()
        usecase = PublishContentUseCase(executor=fake)
        result = usecase.run_legacy_script(
            video_path=Path("/tmp/fake.mp4"),
            script_data={},
            platform="wechat",
            privacy="private",
            account=None,
            keep_wechat_browser_open=False,
        )
        self.assertEqual(fake.calls, ["wechat"])
        self.assertIn("wechat", result)
        self.assertNotIn("youtube", result)

    def test_close_wechat_browser_noop(self):
        fake = _FakeExecutor()
        usecase = PublishContentUseCase(executor=fake)
        self.assertFalse(usecase.close_wechat_browser())
        self.assertEqual(fake.calls, ["close"])


if __name__ == "__main__":
    unittest.main()

