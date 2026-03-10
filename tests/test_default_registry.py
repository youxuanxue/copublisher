import unittest

from copublisher.infrastructure.registry import build_default_registry


class DefaultRegistryTests(unittest.TestCase):
    def test_default_registry_contains_all_supported_platforms(self):
        registry = build_default_registry()
        self.assertEqual(
            set(registry.list_platforms()),
            {"wechat", "youtube", "medium", "twitter", "devto", "tiktok", "instagram"},
        )

    def test_default_registry_capabilities_accessible(self):
        registry = build_default_registry()
        caps = registry.get_capabilities("wechat")
        self.assertIn("content", caps)
        self.assertIn("requires_manual_confirmation", caps)


if __name__ == "__main__":
    unittest.main()

