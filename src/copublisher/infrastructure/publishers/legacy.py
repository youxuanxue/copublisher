"""
Legacy platform adapters implementing PublisherPort.
"""

from __future__ import annotations

import time
from pathlib import Path

from copublisher.domain.error_codes import ErrorCode, get_policy, map_exception_to_error_code
from copublisher.domain.result import PlatformRunOutcome


class LegacyWeChatPublisherAdapter:
    platform = "wechat"

    def publish(
        self,
        *,
        video_path: Path,
        script_data: dict,
        privacy: str,
        account: str | None,
    ) -> PlatformRunOutcome:
        from copublisher.core import WeChatPublishTask, WeChatPublisher

        started = time.perf_counter()
        try:
            task = WeChatPublishTask.from_json(video_path, script_data)
            with WeChatPublisher(headless=False, account=account) as publisher:
                publisher.authenticate()
                success, message = publisher.publish(task)
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            if success:
                return PlatformRunOutcome(
                    platform=self.platform,
                    success=True,
                    message=message or "",
                    duration_ms=elapsed_ms,
                )

            code = ErrorCode.MP_PLATFORM_ERROR
            policy = get_policy(code)
            return PlatformRunOutcome(
                platform=self.platform,
                success=False,
                message=message or "wechat publish failed",
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


class LegacyYouTubePublisherAdapter:
    platform = "youtube"

    def publish(
        self,
        *,
        video_path: Path,
        script_data: dict,
        privacy: str,
        account: str | None,
    ) -> PlatformRunOutcome:
        from copublisher.core import YouTubePublishTask, YouTubePublisher

        del account
        started = time.perf_counter()
        try:
            task = YouTubePublishTask.from_json(video_path, script_data)
            task.privacy_status = privacy
            with YouTubePublisher() as publisher:
                success, video_url = publisher.publish(task)
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            if success:
                return PlatformRunOutcome(
                    platform=self.platform,
                    success=True,
                    message=video_url or "",
                    duration_ms=elapsed_ms,
                )

            code = ErrorCode.MP_PLATFORM_ERROR
            policy = get_policy(code)
            return PlatformRunOutcome(
                platform=self.platform,
                success=False,
                message="youtube publish failed",
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


class LegacyMediumPublisherAdapter:
    platform = "medium"

    def publish(
        self,
        *,
        video_path: Path,
        script_data: dict,
        privacy: str,
        account: str | None,
    ) -> PlatformRunOutcome:
        del video_path, privacy, account
        from copublisher.core import MediumPublishTask, MediumPublisher

        started = time.perf_counter()
        try:
            medium_data = script_data.get("medium", {})
            task = MediumPublishTask(
                title=medium_data.get("title", ""),
                content=medium_data.get("content", medium_data.get("body_markdown", "")),
                tags=medium_data.get("tags", []),
                canonical_url=medium_data.get("canonical_url"),
                publish_status=medium_data.get("publish_status", "draft"),
            )
            with MediumPublisher() as publisher:
                success, detail = publisher.publish(task)
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            if success:
                return PlatformRunOutcome(self.platform, True, detail or "", duration_ms=elapsed_ms)

            code = ErrorCode.MP_PLATFORM_ERROR
            policy = get_policy(code)
            return PlatformRunOutcome(
                platform=self.platform,
                success=False,
                message=detail or "medium publish failed",
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


class LegacyTwitterPublisherAdapter:
    platform = "twitter"

    def publish(
        self,
        *,
        video_path: Path,
        script_data: dict,
        privacy: str,
        account: str | None,
    ) -> PlatformRunOutcome:
        del video_path, privacy, account
        from copublisher.core import TwitterPublishTask, TwitterPublisher

        started = time.perf_counter()
        try:
            twitter_data = script_data.get("twitter", {})
            tweets = twitter_data.get("tweets", [])
            if isinstance(tweets, str):
                tweets = [part.strip() for part in tweets.split("\n\n") if part.strip()]
            task = TwitterPublishTask(
                title=twitter_data.get("title", "thread"),
                tweets=tweets,
                hashtags=twitter_data.get("hashtags", []),
            )
            with TwitterPublisher() as publisher:
                success, detail = publisher.publish(task)
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            if success:
                return PlatformRunOutcome(self.platform, True, detail or "", duration_ms=elapsed_ms)

            code = ErrorCode.MP_PLATFORM_ERROR
            policy = get_policy(code)
            return PlatformRunOutcome(
                platform=self.platform,
                success=False,
                message=detail or "twitter publish failed",
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


class LegacyDevToPublisherAdapter:
    platform = "devto"

    def publish(
        self,
        *,
        video_path: Path,
        script_data: dict,
        privacy: str,
        account: str | None,
    ) -> PlatformRunOutcome:
        del video_path, privacy, account
        from copublisher.core import DevToPublishTask, DevToPublisher

        started = time.perf_counter()
        try:
            devto_data = script_data.get("devto", {})
            task = DevToPublishTask(
                title=devto_data.get("title", ""),
                body_markdown=devto_data.get("body_markdown", ""),
                tags=devto_data.get("tags", []),
                series=devto_data.get("series"),
                canonical_url=devto_data.get("canonical_url"),
                published=bool(devto_data.get("published", False)),
            )
            with DevToPublisher() as publisher:
                success, detail = publisher.publish(task)
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            if success:
                return PlatformRunOutcome(self.platform, True, detail or "", duration_ms=elapsed_ms)

            code = ErrorCode.MP_PLATFORM_ERROR
            policy = get_policy(code)
            return PlatformRunOutcome(
                platform=self.platform,
                success=False,
                message=detail or "devto publish failed",
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


class LegacyTikTokPublisherAdapter:
    platform = "tiktok"

    def publish(
        self,
        *,
        video_path: Path,
        script_data: dict,
        privacy: str,
        account: str | None,
    ) -> PlatformRunOutcome:
        del privacy, account
        from copublisher.core import TikTokPublishTask, TikTokPublisher

        started = time.perf_counter()
        try:
            task = TikTokPublishTask.from_json(video_path, script_data)
            with TikTokPublisher() as publisher:
                success, detail = publisher.publish(task)
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            if success:
                return PlatformRunOutcome(self.platform, True, detail or "", duration_ms=elapsed_ms)

            code = ErrorCode.MP_PLATFORM_ERROR
            policy = get_policy(code)
            return PlatformRunOutcome(
                platform=self.platform,
                success=False,
                message=detail or "tiktok publish failed",
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


class LegacyInstagramPublisherAdapter:
    platform = "instagram"

    def publish(
        self,
        *,
        video_path: Path,
        script_data: dict,
        privacy: str,
        account: str | None,
    ) -> PlatformRunOutcome:
        del privacy, account
        from copublisher.core import InstagramPublishTask, InstagramPublisher

        started = time.perf_counter()
        try:
            task = InstagramPublishTask.from_json(video_path, script_data)
            with InstagramPublisher() as publisher:
                success, detail = publisher.publish(task)
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            if success:
                return PlatformRunOutcome(self.platform, True, detail or "", duration_ms=elapsed_ms)

            code = ErrorCode.MP_PLATFORM_ERROR
            policy = get_policy(code)
            return PlatformRunOutcome(
                platform=self.platform,
                success=False,
                message=detail or "instagram publish failed",
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

