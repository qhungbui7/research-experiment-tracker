from __future__ import annotations

import unittest
from pathlib import Path

from experiment_tracker.builder import build_graph, build_html_data
from experiment_tracker.parsers.context import parse_all_contexts
from experiment_tracker.parsers.markdown import parse_changelog, parse_reviews_readme, parse_tracker
from experiment_tracker.parsers.runs import list_run_dirs

DEMO_DIR = Path(__file__).resolve().parents[1] / "examples" / "demo_project"


class TestBuilder(unittest.TestCase):
    def setUp(self) -> None:
        self.experiments, self.rounds = parse_reviews_readme(DEMO_DIR / "reports" / "reviews" / "README.md")
        self.issues = parse_tracker(DEMO_DIR / "reports" / "reviews" / "TRACKER.md")
        self.changes = parse_changelog(DEMO_DIR / "CHANGELOG.md")
        self.contexts = parse_all_contexts(DEMO_DIR / "reports" / "reviews")
        self.run_dirs = list_run_dirs(DEMO_DIR / "runs")

    def test_build_mermaid_graph(self) -> None:
        mermaid = build_graph(
            experiments=self.experiments,
            rounds=self.rounds,
            issues=self.issues,
            changes=self.changes,
            selected=set(),
            include_issues="all",
            include_changelog=True,
            max_label_len=100,
            root_title="Demo Research Lineage",
            run_dirs=self.run_dirs,
        )

        self.assertIn("flowchart TD", mermaid)
        self.assertIn("experiment_001", mermaid)
        self.assertIn("round_001", mermaid)
        self.assertIn("I-001", mermaid)

    def test_build_html_data(self) -> None:
        data = build_html_data(
            experiments=self.experiments,
            rounds=self.rounds,
            issues=self.issues,
            changes=self.changes,
            selected=set(),
            include_issues="all",
            include_changelog=True,
            contexts=self.contexts,
            run_dirs=self.run_dirs,
            root=DEMO_DIR,
        )

        self.assertIn("nodes", data)
        self.assertIn("edges", data)
        self.assertIn("experiments", data)

        kinds = {n["kind"] for n in data["nodes"]}
        self.assertIn("experiment", kinds)
        self.assertIn("round", kinds)
        self.assertIn("issue", kinds)
        self.assertIn("change", kinds)
        self.assertIn("file", kinds)

        # Check edge relationships
        edge_labels = {e["label"] for e in data["edges"]}
        self.assertIn("round", edge_labels)
        self.assertIn("finding", edge_labels)
        self.assertIn("evidence", edge_labels)


if __name__ == "__main__":
    unittest.main()
