"""
Publisher plugin registry and port abstraction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Protocol

from copublisher.domain.result import PlatformRunOutcome


class PublisherPort(Protocol):
    def publish(
        self,
        *,
        video_path: Path,
        script_data: dict,
        privacy: str,
        account: str | None,
    ) -> PlatformRunOutcome:
        ...


PublisherFactory = Callable[[], PublisherPort]


@dataclass(frozen=True)
class RegistryEntry:
    factory: PublisherFactory
    capabilities: dict[str, object] = field(default_factory=dict)


class PublisherRegistry:
    def __init__(self):
        self._entries: dict[str, RegistryEntry] = {}

    def register(
        self,
        platform: str,
        factory: PublisherFactory,
        capabilities: dict[str, object] | None = None,
    ) -> None:
        normalized = platform.strip().lower()
        if normalized in self._entries:
            raise ValueError(f"platform already registered: {normalized}")
        self._entries[normalized] = RegistryEntry(
            factory=factory,
            capabilities=dict(capabilities or {}),
        )

    def get(self, platform: str) -> PublisherPort:
        normalized = platform.strip().lower()
        if normalized not in self._entries:
            raise KeyError(f"platform not registered: {normalized}")
        return self._entries[normalized].factory()

    def get_capabilities(self, platform: str) -> dict[str, object]:
        normalized = platform.strip().lower()
        if normalized not in self._entries:
            raise KeyError(f"platform not registered: {normalized}")
        return dict(self._entries[normalized].capabilities)

    def list_platforms(self) -> list[str]:
        return sorted(self._entries.keys())

    def list_platforms_by_content_type(self, content_type: str) -> list[str]:
        """按内容类型筛选平台（video | article）。"""
        ct = (content_type or "").strip().lower()
        if not ct:
            return self.list_platforms()
        return sorted(
            p
            for p in self._entries
            if self._entries[p].capabilities.get("content") == ct
        )


def build_default_registry() -> PublisherRegistry:
    from copublisher.infrastructure.publishers.legacy import (
        make_devto_adapter,
        make_instagram_adapter,
        make_medium_adapter,
        make_tiktok_adapter,
        make_twitter_adapter,
        make_wechat_adapter,
        make_youtube_adapter,
    )

    registry = PublisherRegistry()
    registry.register(
        "wechat",
        factory=make_wechat_adapter,
        capabilities={"content": "video", "requires_manual_confirmation": True},
    )
    registry.register(
        "youtube",
        factory=make_youtube_adapter,
        capabilities={"content": "video", "requires_manual_confirmation": False},
    )
    registry.register(
        "medium",
        factory=make_medium_adapter,
        capabilities={"content": "article", "requires_manual_confirmation": False},
    )
    registry.register(
        "twitter",
        factory=make_twitter_adapter,
        capabilities={"content": "article", "requires_manual_confirmation": False},
    )
    registry.register(
        "devto",
        factory=make_devto_adapter,
        capabilities={"content": "article", "requires_manual_confirmation": False},
    )
    registry.register(
        "tiktok",
        factory=make_tiktok_adapter,
        capabilities={"content": "video", "requires_manual_confirmation": True},
    )
    registry.register(
        "instagram",
        factory=make_instagram_adapter,
        capabilities={"content": "video", "requires_manual_confirmation": False},
    )
    return registry

