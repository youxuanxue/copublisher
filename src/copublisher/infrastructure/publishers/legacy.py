"""
Generic publisher adapter implementing PublisherPort.

Replaces 7 per-platform boilerplate classes with a single reusable template.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Any

from copublisher.domain.error_codes import ErrorCode, get_policy, map_exception_to_error_code
from copublisher.domain.result import PlatformRunOutcome


class GenericPublisherAdapter:
    """
    Unified adapter that maps (video_path, script_data, privacy, account)
    to a core Publisher's ``publish()`` call and wraps the result in
    ``PlatformRunOutcome``.

    Each platform instance is created by passing:
      - ``platform``: lowercase platform key
      - ``task_factory``: ``(video_path, script_data, privacy, account) -> task``
      - ``publisher_factory``: ``(log_callback, account) -> Publisher``
    """

    def __init__(
        self,
        platform: str,
        task_factory: Callable[..., Any],
        publisher_factory: Callable[..., Any],
    ):
        self.platform = platform
        self._task_factory = task_factory
        self._publisher_factory = publisher_factory

    def publish(
        self,
        *,
        video_path: Path,
        script_data: dict,
        privacy: str,
        account: str | None,
    ) -> PlatformRunOutcome:
        started = time.perf_counter()
        try:
            task = self._task_factory(
                video_path=video_path,
                script_data=script_data,
                privacy=privacy,
                account=account,
            )
            with self._publisher_factory(account=account) as publisher:
                success, detail = publisher.publish(task)

            elapsed_ms = int((time.perf_counter() - started) * 1000)
            if success:
                return PlatformRunOutcome(
                    platform=self.platform,
                    success=True,
                    message=detail or "",
                    duration_ms=elapsed_ms,
                )

            code = ErrorCode.MP_PLATFORM_ERROR
            policy = get_policy(code)
            return PlatformRunOutcome(
                platform=self.platform,
                success=False,
                message=detail or f"{self.platform} publish failed",
                error_code=code,
                retryable=policy.retryable,
                manual_takeover_required=policy.manual_takeover_required,
                duration_ms=elapsed_ms,
            )
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            code = map_exception_to_error_code(exc)
            policy = get_policy(code)
            return PlatformRunOutcome(
                platform=self.platform,
                success=False,
                message=str(exc),
                error_code=code,
                retryable=policy.retryable,
                manual_takeover_required=policy.manual_takeover_required,
                duration_ms=elapsed_ms,
            )


# ── Per-platform task factories ──────────────────────────────────────

def _wechat_task(*, video_path, script_data, privacy, account):
    from copublisher.core import WeChatPublishTask
    return WeChatPublishTask.from_json(video_path, script_data)


def _youtube_task(*, video_path, script_data, privacy, account):
    from copublisher.core import YouTubePublishTask
    task = YouTubePublishTask.from_json(video_path, script_data)
    task.privacy_status = privacy
    return task


def _medium_task(*, video_path, script_data, privacy, account):
    from copublisher.core import MediumPublishTask
    d = script_data.get("medium", {})
    return MediumPublishTask(
        title=d.get("title", ""),
        content=d.get("content", d.get("body_markdown", "")),
        tags=d.get("tags", []),
        canonical_url=d.get("canonical_url"),
        publish_status=d.get("publish_status", "draft"),
    )


def _twitter_task(*, video_path, script_data, privacy, account):
    from copublisher.core import TwitterPublishTask
    d = script_data.get("twitter", {})
    tweets = d.get("tweets", [])
    if isinstance(tweets, str):
        tweets = [part.strip() for part in tweets.split("\n\n") if part.strip()]
    return TwitterPublishTask(
        title=d.get("title", "thread"),
        tweets=tweets,
        hashtags=d.get("hashtags", []),
    )


def _devto_task(*, video_path, script_data, privacy, account):
    from copublisher.core import DevToPublishTask
    d = script_data.get("devto", {})
    return DevToPublishTask(
        title=d.get("title", ""),
        body_markdown=d.get("body_markdown", ""),
        tags=d.get("tags", []),
        series=d.get("series"),
        canonical_url=d.get("canonical_url"),
        published=bool(d.get("published", False)),
    )


def _tiktok_task(*, video_path, script_data, privacy, account):
    from copublisher.core import TikTokPublishTask
    return TikTokPublishTask.from_json(video_path, script_data)


def _instagram_task(*, video_path, script_data, privacy, account):
    from copublisher.core import InstagramPublishTask
    return InstagramPublishTask.from_json(video_path, script_data)


# ── Per-platform publisher factories ────────────────────────────────

def _wechat_publisher(*, account):
    from copublisher.core import WeChatPublisher
    pub = WeChatPublisher(headless=False, account=account)
    pub.authenticate()
    return pub


def _youtube_publisher(*, account):
    from copublisher.core import YouTubePublisher
    return YouTubePublisher()


def _medium_publisher(*, account):
    from copublisher.core import MediumPublisher
    return MediumPublisher()


def _twitter_publisher(*, account):
    from copublisher.core import TwitterPublisher
    return TwitterPublisher()


def _devto_publisher(*, account):
    from copublisher.core import DevToPublisher
    return DevToPublisher()


def _tiktok_publisher(*, account):
    from copublisher.core import TikTokPublisher
    return TikTokPublisher()


def _instagram_publisher(*, account):
    from copublisher.core import InstagramPublisher
    return InstagramPublisher()


# ── Convenience factories for the Registry ───────────────────────────

def make_wechat_adapter() -> GenericPublisherAdapter:
    return GenericPublisherAdapter("wechat", _wechat_task, _wechat_publisher)


def make_youtube_adapter() -> GenericPublisherAdapter:
    return GenericPublisherAdapter("youtube", _youtube_task, _youtube_publisher)


def make_medium_adapter() -> GenericPublisherAdapter:
    return GenericPublisherAdapter("medium", _medium_task, _medium_publisher)


def make_twitter_adapter() -> GenericPublisherAdapter:
    return GenericPublisherAdapter("twitter", _twitter_task, _twitter_publisher)


def make_devto_adapter() -> GenericPublisherAdapter:
    return GenericPublisherAdapter("devto", _devto_task, _devto_publisher)


def make_tiktok_adapter() -> GenericPublisherAdapter:
    return GenericPublisherAdapter("tiktok", _tiktok_task, _tiktok_publisher)


def make_instagram_adapter() -> GenericPublisherAdapter:
    return GenericPublisherAdapter("instagram", _instagram_task, _instagram_publisher)
