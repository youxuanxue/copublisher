import unittest
from pathlib import Path


class LayeringNoCoreImportsTests(unittest.TestCase):
    def test_application_layer_does_not_import_core(self):
        app_root = Path(__file__).resolve().parents[1] / "src" / "copublisher" / "application"
        for py_file in app_root.rglob("*.py"):
            text = py_file.read_text(encoding="utf-8")
            self.assertNotIn("copublisher.core", text, f"forbidden core import in {py_file}")

    def test_gui_entry_does_not_import_core_directly(self):
        gui_file = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "copublisher"
            / "interfaces"
            / "gui"
            / "app.py"
        )
        text = gui_file.read_text(encoding="utf-8")
        self.assertNotIn("copublisher.core", text)
        self.assertNotIn("from ..core", text)

    def test_interfaces_cli_does_not_import_core_directly(self):
        """interfaces 层不应直接引用 core，应通过 application UseCase。"""
        interfaces_root = Path(__file__).resolve().parents[1] / "src" / "copublisher" / "interfaces"
        for py_file in interfaces_root.rglob("*.py"):
            text = py_file.read_text(encoding="utf-8")
            self.assertNotIn("copublisher.core", text, f"forbidden core import in {py_file}")


if __name__ == "__main__":
    unittest.main()

