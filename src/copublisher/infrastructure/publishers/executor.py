"""
Infrastructure executor that hosts core publisher integrations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable


class LegacyPlatformExecutor:
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
        results: dict[str, tuple[bool, str]] = {}
        normalized = (platform or "wechat").strip().lower()
        selected = ["wechat", "youtube"] if normalized == "both" else [normalized]

        if "wechat" in selected:
            results["wechat"] = self._publish_wechat_from_script(
                video_path=video_path,
                script_data=script_data,
                account=account,
                keep_browser_open=keep_wechat_browser_open,
            )
        if "youtube" in selected:
            results["youtube"] = self._publish_youtube_from_script(
                video_path=video_path,
                script_data=script_data,
                privacy=privacy,
            )
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
        from copublisher.core import (
            DevToPublisher,
            EpisodeAdapter,
            InstagramPublisher,
            MediumPublisher,
            TikTokPublisher,
            TwitterPublisher,
            WeChatPublisher,
            YouTubePublisher,
        )

        adapter = EpisodeAdapter(episode_path)
        results: dict[str, tuple[bool, str]] = {}

        for platform in platforms:
            normalized = platform.strip().lower()
            if normalized in {"wechat", "youtube", "tiktok", "instagram"} and video_path is None:
                results[normalized] = (False, "需要视频文件")
                continue
            try:
                if normalized == "medium":
                    task = adapter.to_medium_task()
                    with MediumPublisher(log_callback=self._log) as publisher:
                        results[normalized] = publisher.publish(task)
                elif normalized == "twitter":
                    task = adapter.to_twitter_task()
                    with TwitterPublisher(log_callback=self._log) as publisher:
                        results[normalized] = publisher.publish(task)
                elif normalized == "devto":
                    task = adapter.to_devto_task()
                    with DevToPublisher(log_callback=self._log) as publisher:
                        results[normalized] = publisher.publish(task)
                elif normalized == "tiktok":
                    task = adapter.to_tiktok_task(video_path)
                    with TikTokPublisher(log_callback=self._log) as publisher:
                        results[normalized] = publisher.publish(task)
                elif normalized == "instagram":
                    task = adapter.to_instagram_task(video_path)
                    with InstagramPublisher(log_callback=self._log) as publisher:
                        results[normalized] = publisher.publish(task)
                elif normalized == "wechat":
                    task = adapter.to_wechat_task(video_path)
                    if keep_wechat_browser_open:
                        if self.wechat_publisher is None:
                            self.wechat_publisher = WeChatPublisher(
                                headless=False,
                                log_callback=self._log,
                                account=account,
                            )
                            self.wechat_publisher.start()
                            self.wechat_publisher.authenticate()
                        results[normalized] = self.wechat_publisher.publish(task)
                    else:
                        with WeChatPublisher(
                            headless=False,
                            log_callback=self._log,
                            account=account,
                        ) as publisher:
                            publisher.authenticate()
                            results[normalized] = publisher.publish(task)
                elif normalized == "youtube":
                    task = adapter.to_youtube_task(video_path)
                    task.privacy_status = privacy
                    with YouTubePublisher(log_callback=self._log) as publisher:
                        results[normalized] = publisher.publish(task)
                else:
                    results[normalized] = (False, f"不支持的平台: {normalized}")
            except Exception as exc:
                results[normalized] = (False, str(exc))
        return results

    def _publish_wechat_from_script(
        self,
        *,
        video_path: Path,
        script_data: dict,
        account: str | None,
        keep_browser_open: bool,
    ) -> tuple[bool, str]:
        from copublisher.core import WeChatPublishTask, WeChatPublisher

        task = WeChatPublishTask.from_json(video_path, script_data)
        if keep_browser_open:
            if self.wechat_publisher is None:
                self.wechat_publisher = WeChatPublisher(
                    headless=False,
                    account=account,
                    log_callback=self._log,
                )
                self.wechat_publisher.start()
                self.wechat_publisher.authenticate()
            return self.wechat_publisher.publish(task)

        with WeChatPublisher(headless=False, account=account, log_callback=self._log) as publisher:
            publisher.authenticate()
            return publisher.publish(task)

    def _publish_youtube_from_script(
        self,
        *,
        video_path: Path,
        script_data: dict,
        privacy: str,
    ) -> tuple[bool, str]:
        from copublisher.core import YouTubePublishTask, YouTubePublisher

        task = YouTubePublishTask.from_json(video_path, script_data)
        task.privacy_status = privacy
        with YouTubePublisher(log_callback=self._log) as publisher:
            return publisher.publish(task)

