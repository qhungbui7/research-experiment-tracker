from __future__ import annotations

import unittest
from pathlib import Path

from experiment_tracker.parsers.context import parse_all_contexts, parse_context_file
from experiment_tracker.parsers.files import extract_paths, file_preview, looks_like_path, normalize_path
from experiment_tracker.parsers.markdown import parse_changelog, parse_reviews_readme, parse_tracker
from experiment_tracker.parsers.runs import load_run_meta

DEMO_DIR = Path(__file__).resolve().parents[1] / "examples" / "demo_project"


class TestParsers(unittest.TestCase):
    def test_looks_like_path(self) -> None:
        self.assertTrue(looks_like_path("runs/baseline/run_summary.json"))
        self.assertTrue(looks_like_path("configs/train.yaml"))
        self.assertTrue(looks_like_path("src/model.py"))
        self.assertFalse(looks_like_path("not a path with spaces"))
        self.assertFalse(looks_like_path("plain_word"))

    def test_normalize_path(self) -> None:
        self.assertEqual(normalize_path("README.md"), "reports/reviews/README.md")
        self.assertEqual(normalize_path("TRACKER.md"), "reports/reviews/TRACKER.md")
        self.assertEqual(normalize_path("experiments/exp1/"), "reports/reviews/experiments/exp1")

    def test_extract_paths(self) -> None:
        text = "Results stored in `runs/baseline/run_summary.json` and checked against configs/baseline.yaml."
        paths = extract_paths(text)
        self.assertIn("runs/baseline/run_summary.json", paths)
        self.assertIn("configs/baseline.yaml", paths)

    def test_parse_reviews_readme(self) -> None:
        readme_path = DEMO_DIR / "reports" / "reviews" / "README.md"
        experiments, rounds = parse_reviews_readme(readme_path)

        self.assertEqual(len(experiments), 1)
        self.assertEqual(experiments[0].experiment, "experiment_001")
        self.assertIn("Soliton", experiments[0].subject)

        self.assertEqual(len(rounds), 1)
        self.assertEqual(rounds[0].round_name, "round_001")
        self.assertEqual(rounds[0].date, "2026-10-01")

    def test_parse_tracker(self) -> None:
        tracker_path = DEMO_DIR / "reports" / "reviews" / "TRACKER.md"
        issues = parse_tracker(tracker_path)

        self.assertEqual(len(issues), 2)
        issue_map = {i.issue_id: i for i in issues}

        self.assertIn("I-001", issue_map)
        self.assertEqual(issue_map["I-001"].severity, "P2")
        self.assertEqual(issue_map["I-001"].status, "open")

        self.assertIn("I-000", issue_map)
        self.assertEqual(issue_map["I-000"].severity, "P1")
        self.assertEqual(issue_map["I-000"].status, "fixed")

    def test_parse_context(self) -> None:
        ctx_path = DEMO_DIR / "reports" / "reviews" / "experiments" / "experiment_001" / "round_001" / "CONTEXT.md"
        ctx = parse_context_file(ctx_path)

        self.assertEqual(ctx.experiment, "experiment_001")
        self.assertEqual(ctx.round_name, "round_001")
        self.assertIn("Soliton", ctx.focus)
        self.assertIn("I-001", ctx.issue_refs)

        all_contexts = parse_all_contexts(DEMO_DIR / "reports" / "reviews")
        self.assertIn(("experiment_001", "round_001"), all_contexts)

    def test_parse_changelog(self) -> None:
        cl_path = DEMO_DIR / "CHANGELOG.md"
        entries = parse_changelog(cl_path)

        self.assertEqual(len(entries), 1)
        self.assertIn("2026-10-01", entries[0].timestamp)
        self.assertIn("experiment_001", entries[0].experiments)
        self.assertIn(("experiment_001", "round_001"), entries[0].rounds)

    def test_file_preview(self) -> None:
        json_path = "runs/baseline/s0/run_summary.json"
        preview = file_preview(json_path, DEMO_DIR)

        self.assertTrue(preview["available"])
        self.assertEqual(preview["format"], "json")
        self.assertIn("speed_ratio", str(preview["text"]))

    def test_load_run_meta(self) -> None:
        run_dir = DEMO_DIR / "runs" / "baseline" / "s0"
        meta = load_run_meta(run_dir)
        self.assertIn("final_metrics", meta)
        self.assertEqual(meta["final_metrics"]["speed_ratio"], 0.998)


if __name__ == "__main__":
    unittest.main()
