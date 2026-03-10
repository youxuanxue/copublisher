import unittest

import copublisher.__main__ as main_mod


class EntryRefactorTests(unittest.TestCase):
    def test_old_publish_functions_removed_from_entry(self):
        self.assertFalse(hasattr(main_mod, "publish_to_wechat"))
        self.assertFalse(hasattr(main_mod, "publish_to_youtube"))

    def test_entry_keeps_compat_job_cli_function(self):
        self.assertTrue(callable(main_mod.run_job_cli))
        self.assertTrue(callable(main_mod.run_legacy_cli))
        self.assertTrue(callable(main_mod.run_episode_cli))


if __name__ == "__main__":
    unittest.main()

