from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_run_meta(tag_dir: Path) -> dict[str, Any]:
    """Return parsed meta.json / metadata.json / metadata.yaml for a run directory."""
    for filename in ("meta.json", "metadata.json", "run_summary.json"):
        p = tag_dir / filename
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pass
    return {}


def list_run_dirs(runs_root: Path) -> list[Path]:
    """Return all completed or recorded run directories under runs_root."""
    if not runs_root.is_dir():
        return []
    dirs: list[Path] = []
    # Check 1 level and 2 levels deep
    for p in sorted(runs_root.iterdir()):
        if not p.is_dir():
            continue
        # If directory contains run artifacts directly
        if (p / "meta.json").exists() or (p / "run_summary.json").exists() or (p / "metadata.yaml").exists() or (p / "model.zip").exists():
            dirs.append(p)
            continue
        # Check subdirectories (e.g. runs/<algo>/<seed> or runs/<date>/<name>)
        for sub in sorted(p.iterdir()):
            if sub.is_dir():
                dirs.append(sub)
    return dirs


def index_completed_runs(report_root: Path) -> tuple[dict[str, Path], set[str]]:
    """Scan report_root for completed run summaries, returning completed and incomplete run sets."""
    completed: dict[str, Path] = {}
    incomplete: set[str] = set()
    if not report_root.exists():
        return completed, incomplete

    for summary_path in sorted(report_root.rglob("run_summary.json")):
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        active_args = summary.get("active_args", {}) if isinstance(summary.get("active_args"), dict) else {}
        run_name = str(active_args.get("report_run_name") or summary_path.parent.name)
        final_metrics = summary.get("final_metrics", {})
        has_metrics = isinstance(final_metrics, dict) and len(final_metrics) > 0

        if has_metrics:
            prev = completed.get(run_name)
            if prev is None or summary_path.stat().st_mtime > prev.stat().st_mtime:
                completed[run_name] = summary_path
            incomplete.discard(run_name)
        elif run_name not in completed:
            incomplete.add(run_name)

    return completed, incomplete
