from __future__ import annotations

import unittest
from pathlib import Path

from experiment_tracker.config import ProjectConfig


class TestProjectConfig(unittest.TestCase):
    def test_default_paths(self) -> None:
        root = Path("/tmp/mock_research_proj")
        cfg = ProjectConfig(root_dir=root, project_name="mock_proj")

        self.assertEqual(cfg.root_dir, root)
        self.assertEqual(cfg.project_name, "mock_proj")
        self.assertEqual(cfg.reviews_dir, root / "reports/reviews")
        self.assertEqual(cfg.experiments_dir, root / "reports/reviews/experiments")
        self.assertEqual(cfg.tracker_file, root / "reports/reviews/TRACKER.md")
        self.assertEqual(cfg.readme_file, root / "reports/reviews/README.md")
        self.assertEqual(cfg.configs_dir, root / "configs")
        self.assertEqual(cfg.runs_dir, root / "runs")
        self.assertEqual(cfg.snapshots_dir, root / "reports/reviews/snapshots")

    def test_discovery_on_demo_project(self) -> None:
        demo_dir = Path(__file__).resolve().parents[1] / "examples" / "demo_project"
        cfg = ProjectConfig.discover(demo_dir)

        self.assertEqual(cfg.project_name, "demo-soliton-research")
        self.assertEqual(cfg.root_dir, demo_dir.resolve())
        self.assertTrue(cfg.readme_file.exists())
        self.assertTrue(cfg.tracker_file.exists())


if __name__ == "__main__":
    unittest.main()
