from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

from .config import ProjectConfig
from .parsers.context import parse_all_contexts
from .parsers.markdown import parse_reviews_readme, parse_tracker
from .parsers.runs import list_run_dirs


class ValidationResult(NamedTuple):
    errors: list[str]
    warnings: list[str]

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


def validate_project(config: ProjectConfig, verbose: bool = False) -> ValidationResult:
    """Check consistency between markdown tables, filesystem, contexts, and tracker issues."""
    errors: list[str] = []
    warnings: list[str] = []

    readme_path = config.readme_file
    tracker_path = config.tracker_file
    reviews_dir = config.reviews_dir

    if not readme_path.exists():
        errors.append(f"Reviews index missing: {readme_path.relative_to(config.root_dir)}")
        return ValidationResult(errors=errors, warnings=warnings)

    experiments, rounds = parse_reviews_readme(readme_path)
    issues = parse_tracker(tracker_path) if tracker_path.exists() else []
    contexts = parse_all_contexts(reviews_dir, config.reviews_dir_name)

    exp_names = {e.experiment for e in experiments}
    round_keys = {(r.experiment, r.round_name) for r in rounds}

    # 1. Experiment folders on disk
    for exp in experiments:
        exp_dir = config.experiments_dir / exp.experiment
        if not exp_dir.is_dir():
            errors.append(f"Experiment folder missing: {exp_dir.relative_to(config.root_dir)}")

    # 2. Context files for rounds
    for round_info in rounds:
        ctx_path = config.experiments_dir / round_info.experiment / round_info.round_name / "CONTEXT.md"
        if not ctx_path.exists():
            errors.append(f"Round CONTEXT.md missing: {ctx_path.relative_to(config.root_dir)}")

    # 3. Discovered context folders without README round entries
    for (ctx_exp, ctx_round) in contexts:
        if (ctx_exp, ctx_round) not in round_keys:
            warnings.append(f"Round on disk not in README.md table: {ctx_exp}/{ctx_round}")

    # 4. Tracker issue references
    for issue in issues:
        if issue.experiment and issue.experiment not in exp_names:
            warnings.append(f"Issue {issue.issue_id} references unknown experiment: {issue.experiment}")
        if issue.experiment and issue.round_name:
            if (issue.experiment, issue.round_name) not in round_keys:
                warnings.append(
                    f"Issue {issue.issue_id} references unknown round: {issue.experiment}/{issue.round_name}"
                )

    # 5. Check reports
    for round_info in rounds:
        if round_info.report:
            rep_path = config.root_dir / round_info.report
            if not rep_path.exists():
                warnings.append(f"Report file referenced in {round_info.round_name} not found: {round_info.report}")

    return ValidationResult(errors=errors, warnings=warnings)
