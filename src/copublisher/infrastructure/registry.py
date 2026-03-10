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


def build_default_registry() -> PublisherRegistry:
    from copublisher.infrastructure.publishers.legacy import (
        LegacyDevToPublisherAdapter,
        LegacyInstagramPublisherAdapter,
        LegacyMediumPublisherAdapter,
        LegacyTikTokPublisherAdapter,
        LegacyTwitterPublisherAdapter,
        LegacyWeChatPublisherAdapter,
        LegacyYouTubePublisherAdapter,
    )

    registry = PublisherRegistry()
    registry.register(
        "wechat",
        factory=LegacyWeChatPublisherAdapter,
        capabilities={"content": "video", "requires_manual_confirmation": True},
    )
    registry.register(
        "youtube",
        factory=LegacyYouTubePublisherAdapter,
        capabilities={"content": "video", "requires_manual_confirmation": False},
    )
    registry.register(
        "medium",
        factory=LegacyMediumPublisherAdapter,
        capabilities={"content": "article", "requires_manual_confirmation": False},
    )
    registry.register(
        "twitter",
        factory=LegacyTwitterPublisherAdapter,
        capabilities={"content": "article", "requires_manual_confirmation": False},
    )
    registry.register(
        "devto",
        factory=LegacyDevToPublisherAdapter,
        capabilities={"content": "article", "requires_manual_confirmation": False},
    )
    registry.register(
        "tiktok",
        factory=LegacyTikTokPublisherAdapter,
        capabilities={"content": "video", "requires_manual_confirmation": True},
    )
    registry.register(
        "instagram",
        factory=LegacyInstagramPublisherAdapter,
        capabilities={"content": "video", "requires_manual_confirmation": False},
    )
    return registry

