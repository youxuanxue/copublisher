import unittest
from pathlib import Path

from copublisher.core.browser import PlaywrightBrowser
from copublisher.shared.security import sanitize_identifier


class SecurityValidationTests(unittest.TestCase):
    def test_sanitize_identifier_accepts_safe_value(self):
        self.assertEqual(sanitize_identifier("agent_01"), "agent_01")
        self.assertEqual(sanitize_identifier("奶奶讲故事"), "奶奶讲故事")

    def test_sanitize_identifier_rejects_path_traversal(self):
        with self.assertRaises(ValueError):
            sanitize_identifier("../evil")

        with self.assertRaises(ValueError):
            sanitize_identifier("a/b")

    def test_browser_rejects_unsafe_user_name(self):
        with self.assertRaises(ValueError):
            PlaywrightBrowser(platform_name="wechat", user_name="../x")

    def test_browser_auth_path_uses_sanitized_user_name(self):
        browser = PlaywrightBrowser(platform_name="wechat", user_name="teamA_01")
        p = browser.auth_file_path
        self.assertIsInstance(p, Path)
        self.assertIn("wechat_auth.json", str(p))
        self.assertIn("teamA_01", str(p))

    def test_browser_auth_path_without_user_name(self):
        browser = PlaywrightBrowser(platform_name="wechat")
        p = browser.auth_file_path
        self.assertIsInstance(p, Path)
        self.assertIn("wechat_auth.json", str(p))


if __name__ == "__main__":
    unittest.main()
