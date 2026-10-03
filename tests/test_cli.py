from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from experiment_tracker.cli import main

DEMO_DIR = Path(__file__).resolve().parents[1] / "examples" / "demo_project"


class TestCLI(unittest.TestCase):
    def test_cli_validate_demo(self) -> None:
        code = main(["--root", str(DEMO_DIR), "validate"])
        self.assertEqual(code, 0)

    def test_cli_build_mermaid(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".md") as f:
            code = main(["--root", str(DEMO_DIR), "build", "--output", f.name, "--format", "mermaid"])
            self.assertEqual(code, 0)
            content = Path(f.name).read_text(encoding="utf-8")
            self.assertIn("flowchart TD", content)
            self.assertIn("experiment_001", content)

    def test_cli_build_html(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".html") as f:
            code = main(["--root", str(DEMO_DIR), "build", "--output", f.name, "--format", "html"])
            self.assertEqual(code, 0)
            content = Path(f.name).read_text(encoding="utf-8")
            self.assertIn("<!doctype html>", content)
            self.assertIn("demo-soliton-research", content)

    def test_cli_init_and_validate_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            # 1. Init new project
            code_init = main(["--root", tmp_dir, "init", "--name", "new-rl-study"])
            self.assertEqual(code_init, 0)

            # 2. Validate
            code_val = main(["--root", tmp_dir, "validate"])
            self.assertEqual(code_val, 0)

            # 3. Status
            code_stat = main(["--root", tmp_dir, "status"])
            self.assertEqual(code_stat, 0)


if __name__ == "__main__":
    unittest.main()
