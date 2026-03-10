import unittest
from pathlib import Path

from copublisher.domain.result import PlatformRunOutcome
from copublisher.infrastructure.registry import PublisherRegistry


class DummyPublisher:
    def __init__(self, platform: str):
        self.platform = platform

    def publish(self, *, video_path: Path, script_data: dict, privacy: str, account: str | None):
        del video_path, script_data, privacy, account
        return PlatformRunOutcome(
            platform=self.platform,
            success=True,
            message="ok",
            duration_ms=1,
        )


class RegistryExtensionTests(unittest.TestCase):
    def test_register_and_get_custom_platform(self):
        registry = PublisherRegistry()
        registry.register(
            "custom",
            factory=lambda: DummyPublisher("custom"),
            capabilities={"content": "article"},
        )

        publisher = registry.get("custom")
        self.assertIsInstance(publisher, DummyPublisher)
        self.assertEqual(registry.list_platforms(), ["custom"])
        self.assertEqual(registry.get_capabilities("custom")["content"], "article")

    def test_register_duplicate_platform_is_rejected(self):
        registry = PublisherRegistry()
        registry.register("custom", factory=lambda: DummyPublisher("custom"))
        with self.assertRaises(ValueError):
            registry.register("custom", factory=lambda: DummyPublisher("custom"))

    def test_get_unknown_platform_raises(self):
        registry = PublisherRegistry()
        with self.assertRaises(KeyError):
            registry.get("unknown")


if __name__ == "__main__":
    unittest.main()

