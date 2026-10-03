from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class ProjectConfig:
    """Project-level configuration and path resolution for experiment tracking."""

    root_dir: Path
    project_name: str = ""
    reviews_dir_name: str = "reports/reviews"
    tracker_file_name: str = "reports/reviews/TRACKER.md"
    readme_file_name: str = "reports/reviews/README.md"
    changelog_file_name: str = "changelog.md"
    runs_dir_name: str = "runs"
    configs_dir_name: str = "configs"
    snapshots_dir_name: str = "reports/reviews/snapshots"

    @property
    def reviews_dir(self) -> Path:
        return self.root_dir / self.reviews_dir_name

    @property
    def experiments_dir(self) -> Path:
        return self.reviews_dir / "experiments"

    @property
    def tracker_file(self) -> Path:
        return self.root_dir / self.tracker_file_name

    @property
    def readme_file(self) -> Path:
        return self.root_dir / self.readme_file_name

    @property
    def changelog_file(self) -> Path:
        # Check lowercase changelog.md then uppercase CHANGELOG.md
        lower = self.root_dir / "changelog.md"
        upper = self.root_dir / "CHANGELOG.md"
        if lower.exists():
            return lower
        if upper.exists():
            return upper
        return self.root_dir / self.changelog_file_name

    @property
    def runs_dir(self) -> Path:
        return self.root_dir / self.runs_dir_name

    @property
    def configs_dir(self) -> Path:
        return self.root_dir / self.configs_dir_name

    @property
    def snapshots_dir(self) -> Path:
        return self.root_dir / self.snapshots_dir_name

    @classmethod
    def discover(cls, start_path: Optional[Path] = None) -> ProjectConfig:
        """Discover the root of the project from start_path or current working dir."""
        current = (start_path or Path.cwd()).resolve()

        # Check for config file (.experiment-tracker.json or .tracker.json)
        for parent in [current, *current.parents]:
            cfg_file = parent / ".experiment-tracker.json"
            if cfg_file.exists():
                try:
                    data = json.loads(cfg_file.read_text(encoding="utf-8"))
                    return cls(
                        root_dir=parent,
                        project_name=data.get("project_name", parent.name),
                        reviews_dir_name=data.get("reviews_dir", "reports/reviews"),
                        tracker_file_name=data.get("tracker_file", "reports/reviews/TRACKER.md"),
                        readme_file_name=data.get("readme_file", "reports/reviews/README.md"),
                        changelog_file_name=data.get("changelog_file", "changelog.md"),
                        runs_dir_name=data.get("runs_dir", "runs"),
                        configs_dir_name=data.get("configs_dir", "configs"),
                        snapshots_dir_name=data.get("snapshots_dir", "reports/reviews/snapshots"),
                    )
                except Exception:
                    pass

        # Check for project markers
        for parent in [current, *current.parents]:
            if (parent / "reports" / "reviews").is_dir() or (parent / ".git").is_dir():
                return cls(root_dir=parent, project_name=parent.name)

        return cls(root_dir=current, project_name=current.name)
