"""research-experiment-tracker: Generalized experiment tracking, review lineage, and methodology framework."""

from __future__ import annotations

from .config import ProjectConfig
from .models import ChangeEntry, Experiment, ExperimentSnapshot, Issue, Round, RoundContext, RunArtifact
from .snapshot import create_snapshot, finalize_snapshot, find_running_snapshot, list_snapshots
from .validator import validate_project

__version__ = "1.0.0"

__all__ = [
    "ProjectConfig",
    "Experiment",
    "Round",
    "Issue",
    "ChangeEntry",
    "RoundContext",
    "ExperimentSnapshot",
    "RunArtifact",
    "create_snapshot",
    "finalize_snapshot",
    "find_running_snapshot",
    "list_snapshots",
    "validate_project",
]
