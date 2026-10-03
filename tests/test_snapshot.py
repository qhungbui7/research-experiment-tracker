from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from experiment_tracker.config import ProjectConfig
from experiment_tracker.snapshot import create_snapshot, finalize_snapshot, list_snapshots


class TestSnapshot(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "configs").mkdir(parents=True)
        (self.root / "configs" / "test.yaml").write_text("param: 42\n", encoding="utf-8")
        (self.root / "changelog.md").write_text("# Changelog\n", encoding="utf-8")
        self.config = ProjectConfig(root_dir=self.root, project_name="test-proj")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_snapshot_lifecycle(self) -> None:
        # 1. Create snapshot
        snap = create_snapshot(
            config=self.config,
            description="Unit test run snapshot",
            run_note="screening test",
            seeds=[0, 1],
            parameters={"lr": 0.001},
            create_git_branch=False,
        )

        self.assertEqual(snap.status, "RUNNING")
        self.assertEqual(snap.description, "Unit test run snapshot")
        self.assertEqual(snap.seeds, [0, 1])

        # Verify disk files
        snap_dir = self.config.snapshots_dir / snap.run_id
        self.assertTrue(snap_dir.is_dir())
        self.assertTrue((snap_dir / "metadata.json").exists())
        self.assertTrue((snap_dir / "configs_snapshot" / "test.yaml").exists())

        # Verify changelog updated
        cl_text = self.config.changelog_file.read_text(encoding="utf-8")
        self.assertIn("Unit test run snapshot", cl_text)
        self.assertIn("Status: RUNNING", cl_text)

        # 2. List snapshots
        snapshots = list_snapshots(self.config)
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0].run_id, snap.run_id)

        # 3. Finalize snapshot
        finalized = finalize_snapshot(
            config=self.config,
            run_id=snap.run_id,
            status="FULL_RUN",
            results_summary={"accuracy": 0.95},
        )

        self.assertIsNotNone(finalized)
        self.assertEqual(finalized.status, "FULL_RUN")
        self.assertEqual(finalized.results_summary["accuracy"], 0.95)

        # Verify changelog updated to FULL_RUN
        cl_text_after = self.config.changelog_file.read_text(encoding="utf-8")
        self.assertIn("Status: FULL_RUN", cl_text_after)


if __name__ == "__main__":
    unittest.main()
