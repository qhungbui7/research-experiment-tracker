from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .config import ProjectConfig

SCAFFOLD_TEMPLATES_DIR = Path(__file__).parent / "templates" / "scaffold"


def init_project(
    root: Path,
    project_name: str = "",
    force: bool = False,
) -> list[str]:
    """Scaffold a project with standard experiment tracking directories and templates."""
    root = root.resolve()
    name = project_name or root.name
    created: list[str] = []

    config = ProjectConfig(root_dir=root, project_name=name)

    # 1. Directories
    exp1_round1 = config.experiments_dir / "experiment_001" / "round_001"
    for d in (
        config.reviews_dir,
        config.experiments_dir,
        exp1_round1 / "review",
        exp1_round1 / "rebuttals",
        config.snapshots_dir,
        config.configs_dir,
        config.runs_dir,
    ):
        d.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")

    # 2. Config file
    cfg_file = root / ".experiment-tracker.json"
    if not cfg_file.exists() or force:
        cfg_data = {
            "project_name": name,
            "reviews_dir": config.reviews_dir_name,
            "tracker_file": config.tracker_file_name,
            "readme_file": config.readme_file_name,
            "changelog_file": config.changelog_file_name,
            "runs_dir": config.runs_dir_name,
            "configs_dir": config.configs_dir_name,
            "snapshots_dir": config.snapshots_dir_name,
        }
        cfg_file.write_text(json.dumps(cfg_data, indent=2), encoding="utf-8")
        created.append(str(cfg_file.relative_to(root)))

    # 3. Reviews README
    readme_path = config.readme_file
    if not readme_path.exists() or force:
        tpl = (SCAFFOLD_TEMPLATES_DIR / "README.md").read_text(encoding="utf-8")
        content = tpl.replace("YYYY-MM-DD", today)
        readme_path.parent.mkdir(parents=True, exist_ok=True)
        readme_path.write_text(content, encoding="utf-8")
        created.append(str(readme_path.relative_to(root)))

    # 4. TRACKER.md
    tracker_path = config.tracker_file
    if not tracker_path.exists() or force:
        tpl = (SCAFFOLD_TEMPLATES_DIR / "TRACKER.md").read_text(encoding="utf-8")
        tracker_path.parent.mkdir(parents=True, exist_ok=True)
        tracker_path.write_text(tpl, encoding="utf-8")
        created.append(str(tracker_path.relative_to(root)))

    # 5. Round CONTEXT.md
    ctx_path = exp1_round1 / "CONTEXT.md"
    if not ctx_path.exists() or force:
        tpl = (SCAFFOLD_TEMPLATES_DIR / "CONTEXT.md").read_text(encoding="utf-8")
        content = tpl.replace("YYYY-MM-DD", today)
        ctx_path.write_text(content, encoding="utf-8")
        created.append(str(ctx_path.relative_to(root)))

    # 6. Changelog
    changelog_path = config.changelog_file
    if not changelog_path.exists() or force:
        changelog_content = f"# Changelog\n\n## [{today}] -- Initial experiment tracking setup\n- Initialized research experiment tracking structure and review indices.\n"
        changelog_path.write_text(changelog_content, encoding="utf-8")
        created.append(str(changelog_path.relative_to(root)))

    return created
