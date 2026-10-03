from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


OPEN_STATUSES = {"open", "partial", "pending"}
VALID_SEVERITIES = ["P0", "P1", "P2", "P3", "P4"]


@dataclass(frozen=True)
class Experiment:
    experiment: str
    subject: str
    evidence_base: str
    rounds: str
    open_issues: str = ""
    status: str = "active"


@dataclass(frozen=True)
class Round:
    """One review or evaluation pass for an experiment."""

    experiment: str
    round_name: str
    date: str
    focus: str
    trigger: str
    report: str
    open_issues: str = ""


@dataclass(frozen=True)
class Issue:
    """One tracker finding with evidence, severity level, and an optional next step."""

    issue_id: str
    severity: str
    status: str
    experiment: str
    round_name: str
    title: str
    evidence: str
    next_step: str
    source_section: str = ""
    resolved_in: str = ""
    notes: str = ""
    files_changed: tuple[str, ...] = ()


@dataclass(frozen=True)
class ChangeEntry:
    """One changelog entry, plus references discovered in its body."""

    timestamp: str
    title: str
    body: str
    files: tuple[str, ...] = ()
    experiments: tuple[str, ...] = ()
    rounds: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class RoundContext:
    """Parsed content of a round's CONTEXT.md file."""

    experiment: str
    round_name: str
    trigger: str
    focus: str
    what_changed: str
    evidence_summary: str
    open_issues_before: str
    issue_refs: tuple[str, ...] = ()
    file_paths: tuple[str, ...] = ()
    reviewers: str = ""
    outcome: str = ""
    issues_opened: str = ""
    issues_resolved: str = ""


@dataclass
class ExperimentSnapshot:
    """Metadata recorded before and during an experiment execution."""

    run_id: str
    timestamp: str
    description: str
    base_commit: str
    branch: str
    report_dir: str
    run_note: str
    status: str = "RUNNING"
    uncommitted_changes: str = "none"
    configs_snapshot: str = ""
    start_time: str = ""
    end_time: str = ""
    seeds: list[int] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)
    results_summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "description": self.description,
            "base_commit": self.base_commit,
            "branch": self.branch,
            "report_dir": self.report_dir,
            "run_note": self.run_note,
            "status": self.status,
            "uncommitted_changes": self.uncommitted_changes,
            "configs_snapshot": self.configs_snapshot,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "seeds": self.seeds,
            "parameters": self.parameters,
            "results_summary": self.results_summary,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExperimentSnapshot:
        return cls(
            run_id=data.get("run_id", ""),
            timestamp=data.get("timestamp", ""),
            description=data.get("description", ""),
            base_commit=data.get("base_commit", ""),
            branch=data.get("branch", ""),
            report_dir=data.get("report_dir", ""),
            run_note=data.get("run_note", ""),
            status=data.get("status", "RUNNING"),
            uncommitted_changes=data.get("uncommitted_changes", "none"),
            configs_snapshot=data.get("configs_snapshot", ""),
            start_time=data.get("start_time", ""),
            end_time=data.get("end_time", ""),
            seeds=data.get("seeds", []),
            parameters=data.get("parameters", {}),
            results_summary=data.get("results_summary", {}),
        )


@dataclass(frozen=True)
class RunArtifact:
    """An artifact produced by an executed run (metrics, summary, log, model)."""

    run_dir: str
    run_name: str
    algo_or_method: str = ""
    seed: int | None = None
    summary_data: dict[str, Any] = field(default_factory=dict)
    has_metrics: bool = False
