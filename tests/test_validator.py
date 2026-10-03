from __future__ import annotations

import unittest
from pathlib import Path

from experiment_tracker.config import ProjectConfig
from experiment_tracker.validator import validate_project

DEMO_DIR = Path(__file__).resolve().parents[1] / "examples" / "demo_project"


class TestValidator(unittest.TestCase):
    def test_demo_project_validation(self) -> None:
        cfg = ProjectConfig.discover(DEMO_DIR)
        result = validate_project(cfg, verbose=True)

        self.assertTrue(result.is_valid, f"Demo project had errors: {result.errors}")
        self.assertEqual(len(result.errors), 0)


if __name__ == "__main__":
    unittest.main()
