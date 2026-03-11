"""
Infrastructure executor that routes publish requests through the Registry.

Replaces the previous per-platform if/elif dispatch with a unified
Registry-driven path.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from copublisher.domain.result import PlatformRunOutcome


class LegacyPlatformExecutor:
    """
    Executes publish operations for both legacy-script and episode-adapter
    flows.  All platform dispatch goes through ``PublisherRegistry``,
    eliminating the previous dual-path inconsistency.
    """

    def __init__(self, log_callback: Callable[[str], None] | None = None):
        self.log_callback = log_callback
        self.wechat_publisher = None

    def _log(self, message: str) -> None:
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)

    def close_wechat_browser(self) -> bool:
        if self.wechat_publisher:
            self.wechat_publisher.close()
            self.wechat_publisher = None
            return True
        return False

    def load_episode_overview(self, *, episode_path: Path) -> tuple[str, str]:
        from copublisher.core import EpisodeAdapter

        adapter = EpisodeAdapter(episode_path)
        platforms = adapter.get_available_platforms()
        ready = [
            p for p, info in platforms.items() if info["has_content"] and info["has_config"]
        ]
        summary = (
            f"系列: {adapter.series_info.get('series_name', '未知')}\n"
            f"集数: 第 {adapter.episode_number} 集\n"
            f"标题: {adapter.meta.get('title', '未知')}\n"
            f"可发布平台: {', '.join(ready)}"
        )
        blog_text = adapter.content.get("overseas_blog", {}).get("text", "")
        preview = blog_text[:500] + "..." if len(blog_text) > 500 else blog_text
        return summary, preview

    def run_legacy_script(
        self,
        *,
        video_path: Path,
        script_data: dict,
        platform: str,
        privacy: str,
        account: str | None,
        keep_wechat_browser_open: bool = False,
    ) -> dict[str, tuple[bool, str]]:
        normalized = (platform or "wechat").strip().lower()
        selected = ["wechat", "youtube"] if normalized == "both" else [normalized]

        results: dict[str, tuple[bool, str]] = {}
        for plat in selected:
            if plat == "wechat" and keep_wechat_browser_open:
                results[plat] = self._publish_wechat_keep_browser(
                    video_path=video_path,
                    script_data=script_data,
                    account=account,
                )
            else:
                outcome = self._publish_via_registry(
                    platform=plat,
                    video_path=video_path,
                    script_data=script_data,
                    privacy=privacy,
                    account=account,
                )
                results[plat] = (outcome.success, outcome.message)
        return results

    def run_episode_adapter(
        self,
        *,
        episode_path: Path,
        platforms: list[str],
        video_path: Path | None,
        privacy: str,
        account: str | None,
        keep_wechat_browser_open: bool = False,
    ) -> dict[str, tuple[bool, str]]:
        from copublisher.core import EpisodeAdapter

        adapter = EpisodeAdapter(episode_path)
        results: dict[str, tuple[bool, str]] = {}

        for platform in platforms:
            normalized = platform.strip().lower()
            if normalized in {"wechat", "youtube", "tiktok", "instagram"} and video_path is None:
                results[normalized] = (False, "需要视频文件")
                continue
            try:
                script_data = self._episode_to_script_data(adapter, normalized, video_path)

                if normalized == "wechat" and keep_wechat_browser_open:
                    results[normalized] = self._publish_wechat_keep_browser(
                        video_path=video_path or Path("."),
                        script_data=script_data,
                        account=account,
                    )
                else:
                    outcome = self._publish_via_registry(
                        platform=normalized,
                        video_path=video_path or Path("."),
                        script_data=script_data,
                        privacy=privacy,
                        account=account,
                    )
                    results[normalized] = (outcome.success, outcome.message)
            except Exception as exc:
                results[normalized] = (False, str(exc))
        return results

    # ── internal helpers ─────────────────────────────────────────────

    def _publish_via_registry(
        self,
        *,
        platform: str,
        video_path: Path,
        script_data: dict,
        privacy: str,
        account: str | None,
    ) -> PlatformRunOutcome:
        from copublisher.infrastructure.registry import build_default_registry

        registry = build_default_registry()
        adapter = registry.get(platform)
        return adapter.publish(
            video_path=video_path,
            script_data=script_data,
            privacy=privacy,
            account=account,
        )

    def _publish_wechat_keep_browser(
        self,
        *,
        video_path: Path,
        script_data: dict,
        account: str | None,
    ) -> tuple[bool, str]:
        from copublisher.core import WeChatPublishTask, WeChatPublisher

        task = WeChatPublishTask.from_json(video_path, script_data)
        if self.wechat_publisher is None:
            self.wechat_publisher = WeChatPublisher(
                headless=False,
                log_callback=self._log,
                account=account,
            )
            self.wechat_publisher.start()
            self.wechat_publisher.authenticate()
        return self.wechat_publisher.publish(task)

    @staticmethod
    def _episode_to_script_data(adapter, platform: str, video_path: Path | None) -> dict:
        """Convert EpisodeAdapter data into a flat script_data dict the adapters understand."""
        if platform == "medium":
            task = adapter.to_medium_task()
            return {"medium": {
                "title": task.title, "content": task.content,
                "tags": task.tags, "canonical_url": task.canonical_url,
                "publish_status": task.publish_status,
            }}
        if platform == "twitter":
            task = adapter.to_twitter_task()
            return {"twitter": {
                "title": task.title, "tweets": task.tweets,
                "hashtags": task.hashtags,
            }}
        if platform == "devto":
            task = adapter.to_devto_task()
            return {"devto": {
                "title": task.title, "body_markdown": task.body_markdown,
                "tags": task.tags, "series": task.series,
                "canonical_url": task.canonical_url,
                "published": task.published,
            }}
        if platform == "tiktok":
            task = adapter.to_tiktok_task(video_path)
            return {"tiktok": {
                "description": task.description,
                "privacy": task.privacy,
            }}
        if platform == "instagram":
            task = adapter.to_instagram_task(video_path)
            return {"instagram": {
                "caption": task.caption,
                "privacy": task.privacy,
            }}
        if platform == "wechat":
            task = adapter.to_wechat_task(video_path)
            return {"wechat": {
                "title": task.title,
                "description": task.description,
                "hashtags": task.hashtags,
            }}
        if platform == "youtube":
            task = adapter.to_youtube_task(video_path)
            return {"youtube": {
                "title": task.title,
                "description": task.description,
                "tags": task.tags,
                "privacy": task.privacy_status,
            }}
        raise ValueError(f"不支持的平台: {platform}")
