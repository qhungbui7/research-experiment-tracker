from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .config import ProjectConfig
from .models import ExperimentSnapshot
from .parsers.git import get_current_git_ref, git_diff_stat, git_short_hash, run_git_command

VALID_STATUSES = ["FULL_RUN", "BUG_RUN", "OBJ_TERMINATED", "HUMAN_TERMINATED", "PARTIAL", "STOPPED"]


def _run_git(cmd: list[str], root: Path, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=root)
    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"Git command failed: {' '.join(cmd)}\n{detail}")
    return result


def _copy_config_snapshot(src_dir: Path, dst_dir: Path) -> None:
    if not src_dir.exists():
        return
    dst_dir.mkdir(parents=True, exist_ok=True)
    for p in src_dir.rglob("*"):
        if p.is_file() and p.suffix in (".yaml", ".yml", ".json", ".toml", ".ini"):
            rel = p.relative_to(src_dir)
            target = dst_dir / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, target)


def _update_changelog_experiment_status(
    changelog_path: Path,
    run_id: str,
    status: str,
    end_time: str,
) -> None:
    if not changelog_path.exists():
        return
    content = changelog_path.read_text(encoding="utf-8", errors="replace")
    lines = content.splitlines()
    target_marker = f"run_{run_id}" if not run_id.startswith("run_") else run_id

    for idx, line in enumerate(lines):
        if target_marker in line or f"- Snapshot: " in line and run_id in line:
            block_end = len(lines)
            for j in range(idx + 1, len(lines)):
                if lines[j].startswith("## "):
                    block_end = j
                    break
            status_line = f"- Status: {status}"
            end_line = f"- End: {end_time}"
            end_idx = None
            status_idx = None
            for j in range(idx + 1, block_end):
                if lines[j].startswith("- End: "):
                    end_idx = j
                elif lines[j].startswith("- Status: "):
                    status_idx = j
            if end_idx is None:
                lines.insert(idx + 1, end_line)
                block_end += 1
            else:
                lines[end_idx] = end_line
            if status_idx is None:
                lines.insert(block_end, status_line)
            else:
                lines[status_idx] = status_line
            changelog_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return


def create_snapshot(
    config: ProjectConfig,
    description: str,
    run_id: Optional[str] = None,
    run_note: str = "",
    parameters: Optional[dict[str, Any]] = None,
    seeds: Optional[list[int]] = None,
    create_git_branch: bool = False,
    dry_run: bool = False,
) -> ExperimentSnapshot:
    """Create an immutable snapshot of configuration, git state, and experiment parameters."""
    now = datetime.now()
    ts_folder = now.strftime("%Y%m%d_%H%M%S")
    ts_display = now.strftime("%Y-%m-%d %H:%M:%S")

    final_run_id = run_id or f"run_{ts_folder}"
    branch_name = f"exp/{config.project_name or config.root_dir.name}/{ts_folder}"
    commit_hash = git_short_hash(config.root_dir)
    diff_stat = git_diff_stat(config.root_dir)

    snapshot_dir = config.snapshots_dir / final_run_id
    rel_snapshot_dir = str(snapshot_dir.relative_to(config.root_dir))

    snapshot = ExperimentSnapshot(
        run_id=final_run_id,
        timestamp=ts_display,
        description=description,
        base_commit=commit_hash,
        branch=branch_name if create_git_branch else "current",
        report_dir=rel_snapshot_dir,
        run_note=run_note,
        status="RUNNING",
        uncommitted_changes=diff_stat or "clean",
        configs_snapshot=f"{rel_snapshot_dir}/configs_snapshot",
        start_time=ts_display,
        seeds=seeds or [],
        parameters=parameters or {},
    )

    if dry_run:
        return snapshot

    # Materialize snapshot on disk
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    _copy_config_snapshot(config.configs_dir, snapshot_dir / "configs_snapshot")
    meta_path = snapshot_dir / "metadata.json"
    meta_path.write_text(json.dumps(snapshot.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    # Git branch creation if requested
    if create_git_branch:
        start_ref = get_current_git_ref(config.root_dir)
        switched = False
        try:
            _run_git(["git", "checkout", "-b", branch_name], config.root_dir)
            switched = True
            _run_git(["git", "add", str(snapshot_dir.relative_to(config.root_dir))], config.root_dir)
            commit_msg = f"exp({config.project_name}): {description} [{ts_display}]"
            _run_git(["git", "commit", "-m", commit_msg, "--allow-empty"], config.root_dir)
            _run_git(["git", "push", "origin", branch_name], config.root_dir, check=False)
        except Exception:
            pass
        finally:
            if switched:
                _run_git(["git", "checkout", start_ref], config.root_dir, check=False)
            # Re-materialize locally so files exist in current worktree
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            _copy_config_snapshot(config.configs_dir, snapshot_dir / "configs_snapshot")
            meta_path.write_text(json.dumps(snapshot.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    # Update changelog
    changelog_path = config.changelog_file
    if changelog_path.exists():
        entry = (
            f"\n## [{ts_display}] -- Experiment: {description}\n"
            f"- Snapshot: {rel_snapshot_dir}/\n"
            f"- Base commit: {commit_hash}\n"
            f"- Status: RUNNING\n"
        )
        if run_note:
            entry += f"- Note: {run_note}\n"
        content = changelog_path.read_text(encoding="utf-8", errors="replace")
        if "# Changelog" in content:
            new_content = content.replace("# Changelog\n", f"# Changelog\n{entry}", 1)
        else:
            new_content = f"# Changelog\n{entry}\n" + content
        changelog_path.write_text(new_content, encoding="utf-8")

    return snapshot


def finalize_snapshot(
    config: ProjectConfig,
    run_id: str,
    status: str = "FULL_RUN",
    results_summary: Optional[dict[str, Any]] = None,
) -> Optional[ExperimentSnapshot]:
    """Finalize an experiment snapshot with its terminal status and results summary."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    snapshot_dir = config.snapshots_dir / run_id
    if not snapshot_dir.is_dir():
        # Check without run_ prefix
        for d in config.snapshots_dir.glob(f"*{run_id}*"):
            if d.is_dir():
                snapshot_dir = d
                break

    meta_path = snapshot_dir / "metadata.json"
    if not meta_path.exists():
        return None

    try:
        data = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        data = {}

    data["status"] = status
    data["end_time"] = now_str
    if results_summary:
        data["results_summary"] = results_summary

    meta_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    _update_changelog_experiment_status(
        config.changelog_file,
        run_id=snapshot_dir.name,
        status=status,
        end_time=now_str,
    )

    return ExperimentSnapshot.from_dict(data)


def list_snapshots(config: ProjectConfig) -> list[ExperimentSnapshot]:
    """List all saved experiment snapshots in the project."""
    snapshots: list[ExperimentSnapshot] = []
    if not config.snapshots_dir.is_dir():
        return snapshots
    for d in sorted(config.snapshots_dir.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        meta_path = d / "metadata.json"
        if meta_path.exists():
            try:
                data = json.loads(meta_path.read_text(encoding="utf-8"))
                snapshots.append(ExperimentSnapshot.from_dict(data))
            except Exception:
                pass
    return snapshots


def find_running_snapshot(config: ProjectConfig) -> Optional[ExperimentSnapshot]:
    """Find any currently running experiment snapshot."""
    for snap in list_snapshots(config):
        if snap.status.upper() == "RUNNING":
            return snap
    return None
