from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .builder import build_graph, build_html_data
from .config import ProjectConfig
from .exporters import render_html, write_html_export, write_output
from .models import OPEN_STATUSES
from .parsers.context import parse_all_contexts
from .parsers.git import load_commits
from .parsers.markdown import parse_changelog, parse_reviews_readme, parse_tracker
from .parsers.runs import list_run_dirs
from .scaffold import init_project
from .server import serve_dashboard
from .snapshot import create_snapshot, finalize_snapshot, find_running_snapshot, list_snapshots
from .validator import validate_project


def build_command(args: argparse.Namespace, config: ProjectConfig) -> int:
    """Build IDEA_GRAPH.html, IDEA_GRAPH.md, or folder export."""
    readme_path = Path(args.reviews_readme) if getattr(args, "reviews_readme", None) else config.readme_file
    tracker_path = Path(args.tracker) if getattr(args, "tracker", None) else config.tracker_file
    changelog_path = Path(args.changelog) if getattr(args, "changelog", None) else config.changelog_file
    reviews_dir = Path(args.reviews_dir) if getattr(args, "reviews_dir", None) else config.reviews_dir

    if not readme_path.exists():
        print(f"Error: Reviews index file not found at {readme_path}")
        print("Run `experiment-tracker init` to scaffold a new tracking structure.")
        return 1

    experiments, rounds = parse_reviews_readme(readme_path)
    issues = parse_tracker(tracker_path) if tracker_path.exists() else []
    changes = [] if getattr(args, "no_changelog", False) else parse_changelog(changelog_path, config.reviews_dir_name)
    contexts = parse_all_contexts(reviews_dir, config.reviews_dir_name)
    run_dirs = None if getattr(args, "no_runs", False) else list_run_dirs(config.runs_dir)
    commits = None if getattr(args, "no_git", False) else load_commits(config.root_dir)
    snapshots = list_snapshots(config)

    selected = set(getattr(args, "experiment", []) or [])
    include_issues = getattr(args, "include_issues", "all")
    include_changelog = not getattr(args, "no_changelog", False)
    max_label_len = getattr(args, "max_label_len", 110)
    title = getattr(args, "title", None) or f"{config.project_name or config.root_dir.name} Review & Experiment Lineage"

    output_path: Path | None = getattr(args, "output", None)
    output_dir: Path | None = getattr(args, "output_dir", None)
    fmt = getattr(args, "format", None)

    # If neither output nor output_dir is specified, default to IDEA_GRAPH.html in reviews_dir
    if not output_path and not output_dir and not fmt:
        output_path = reviews_dir / "IDEA_GRAPH.html"
        fmt = "html"

    if output_dir:
        print(f"Building folder export in {output_dir}...")
        data = build_html_data(
            experiments=experiments,
            rounds=rounds,
            issues=issues,
            changes=changes,
            selected=selected,
            include_issues=include_issues,
            include_changelog=include_changelog,
            contexts=contexts,
            run_dirs=run_dirs,
            commits=commits,
            snapshots=snapshots,
            root=config.root_dir,
            reviews_dir_prefix=config.reviews_dir_name,
        )
        write_html_export(
            data=data,
            output_dir=output_dir,
            title=title,
            root=config.root_dir,
            reviews_dir_prefix=config.reviews_dir_name,
        )
        print(f"✓ Folder export written to {output_dir}/index.html")

    if output_path or fmt:
        target_fmt = fmt or ("mermaid" if output_path and output_path.suffix == ".md" else "html")

        if target_fmt == "mermaid":
            mermaid_source = build_graph(
                experiments=experiments,
                rounds=rounds,
                issues=issues,
                changes=changes,
                selected=selected,
                include_issues=include_issues,
                include_changelog=include_changelog,
                max_label_len=max_label_len,
                root_title=title,
                run_dirs=run_dirs,
                reviews_dir_prefix=config.reviews_dir_name,
            )
            content = f"```mermaid\n{mermaid_source}```\n" if output_path and output_path.suffix == ".md" else mermaid_source
            if output_path:
                write_output(content, output_path)
                print(f"✓ Mermaid graph written to {output_path}")
            else:
                sys.stdout.write(content)

        elif target_fmt == "html":
            data = build_html_data(
                experiments=experiments,
                rounds=rounds,
                issues=issues,
                changes=changes,
                selected=selected,
                include_issues=include_issues,
                include_changelog=include_changelog,
                contexts=contexts,
                run_dirs=run_dirs,
                commits=commits,
                snapshots=snapshots,
                root=config.root_dir,
                reviews_dir_prefix=config.reviews_dir_name,
            )
            html_content = render_html(data, title)
            dest = output_path or (reviews_dir / "IDEA_GRAPH.html")
            write_output(html_content, dest)
            print(f"✓ Interactive HTML explorer written to {dest}")

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="experiment-tracker",
        description="General Experiment Tracking, Review Lineage & Research Methodology Toolkit",
    )
    parser.add_argument("--root", type=Path, help="Project root directory (auto-discovered if omitted)")

    subparsers = parser.add_subparsers(dest="command")

    # Command: init
    init_parser = subparsers.add_parser("init", help="Scaffold experiment tracking in a project")
    init_parser.add_argument("--name", type=str, help="Project name")
    init_parser.add_argument("--force", action="store_true", help="Overwrite existing files")

    # Command: validate
    val_parser = subparsers.add_parser("validate", help="Validate experiment tracking consistency")
    val_parser.add_argument("--verbose", action="store_true", help="Include informational warnings")

    # Command: build
    build_parser = subparsers.add_parser("build", help="Build interactive graph or Mermaid export")
    build_parser.add_argument("--output", type=Path, help="Output file path (.html or .md)")
    build_parser.add_argument("--output-dir", type=Path, help="Output folder export directory")
    build_parser.add_argument("--format", choices=("html", "mermaid"), help="Output format")
    build_parser.add_argument("--experiment", action="append", help="Filter by experiment (repeatable)")
    build_parser.add_argument("--include-issues", choices=("open", "all", "none"), default="all")
    build_parser.add_argument("--no-changelog", action="store_true", help="Skip changelog nodes")
    build_parser.add_argument("--no-runs", action="store_true", help="Skip run directory nodes")
    build_parser.add_argument("--no-git", action="store_true", help="Skip git commit nodes")
    build_parser.add_argument("--title", type=str, help="Graph title")

    # Command: snapshot
    snap_parser = subparsers.add_parser("snapshot", help="Record pre-run config snapshot and metadata")
    snap_parser.add_argument("--description", "-d", required=True, help="Experiment description")
    snap_parser.add_argument("--note", type=str, default="", help="Run note")
    snap_parser.add_argument("--run-id", type=str, help="Explicit run ID")
    snap_parser.add_argument("--seeds", type=str, help="Comma-separated seed integers")
    snap_parser.add_argument("--git-branch", action="store_true", help="Create and push git tracking branch")
    snap_parser.add_argument("--dry-run", action="store_true", help="Preview snapshot without writing files")

    # Command: finalize
    fin_parser = subparsers.add_parser("finalize", help="Finalize experiment snapshot status and results")
    fin_parser.add_argument("--run-id", required=True, help="Run ID to finalize")
    fin_parser.add_argument(
        "--status",
        choices=["FULL_RUN", "BUG_RUN", "OBJ_TERMINATED", "HUMAN_TERMINATED", "PARTIAL", "STOPPED"],
        default="FULL_RUN",
        help="Final run status",
    )
    fin_parser.add_argument("--summary-json", type=Path, help="Path to run_summary.json metrics")

    # Command: serve
    serve_parser = subparsers.add_parser("serve", help="Serve interactive dashboard via local HTTP")
    serve_parser.add_argument("--port", type=int, default=8080, help="Port (default: 8080)")
    serve_parser.add_argument("--open", action="store_true", help="Open in browser")
    serve_parser.add_argument("--rebuild", action="store_true", help="Rebuild graph before serving")

    # Command: status
    status_parser = subparsers.add_parser("status", help="Show overview of experiments and runs")

    # Backward-compatible flags on root parser
    parser.add_argument("--validate", action="store_true", help="Legacy flag: check consistency and exit")
    parser.add_argument("--reviews-readme", type=Path, help="Legacy flag: path to reviews README.md")
    parser.add_argument("--tracker", type=Path, help="Legacy flag: path to TRACKER.md")
    parser.add_argument("--changelog", type=Path, help="Legacy flag: path to changelog.md")
    parser.add_argument("--reviews-dir", type=Path, help="Legacy flag: path to reviews directory")
    parser.add_argument("--experiment", action="append", help="Legacy flag: filter by experiment")
    parser.add_argument("--include-issues", choices=("open", "all", "none"), default="all")
    parser.add_argument("--no-changelog", action="store_true", help="Legacy flag")
    parser.add_argument("--no-runs", action="store_true", help="Legacy flag")
    parser.add_argument("--no-git", action="store_true", help="Legacy flag")
    parser.add_argument("--output", type=Path, help="Legacy flag: output file path")
    parser.add_argument("--output-dir", type=Path, help="Legacy flag: output folder export")
    parser.add_argument("--format", choices=("html", "mermaid"), help="Legacy flag")
    parser.add_argument("--verbose", action="store_true", help="Legacy flag: verbose validation")
    parser.add_argument("--title", type=str, help="Legacy flag")

    args = parser.parse_args(argv)

    root_path = args.root if args.root else None
    config = ProjectConfig.discover(root_path)

    # Legacy flag dispatch: if --validate was passed directly
    if args.validate or args.command == "validate":
        res = validate_project(config, verbose=args.verbose)
        if res.errors:
            print(f"Validation FAILED ({len(res.errors)} errors):")
            for err in res.errors:
                print(f"  ❌ {err}")
            return 1
        if args.verbose and res.warnings:
            print(f"Validation warnings ({len(res.warnings)} warnings):")
            for warn in res.warnings:
                print(f"  ⚠️  {warn}")
        print("✓ Experiment tracking structure and references are valid.")
        return 0

    if args.command == "init":
        created = init_project(config.root_dir, project_name=args.name or "", force=args.force)
        print(f"✓ Initialized research experiment tracking structure in {config.root_dir}:")
        for p in created:
            print(f"  + {p}")
        return 0

    if args.command == "snapshot":
        seeds = [int(s.strip()) for s in args.seeds.split(",")] if args.seeds else []
        snap = create_snapshot(
            config=config,
            description=args.description,
            run_id=args.run_id,
            run_note=args.note,
            seeds=seeds,
            create_git_branch=args.git_branch,
            dry_run=args.dry_run,
        )
        print(f"✓ Snapshot created: {snap.run_id}")
        print(f"  Description: {snap.description}")
        print(f"  Commit: {snap.base_commit}")
        print(f"  Status: {snap.status}")
        print(f"  Dir: {snap.report_dir}")
        return 0

    if args.command == "finalize":
        summary_data = {}
        if args.summary_json and args.summary_json.exists():
            try:
                summary_data = json.loads(args.summary_json.read_text(encoding="utf-8"))
            except Exception:
                pass
        finalized = finalize_snapshot(
            config=config,
            run_id=args.run_id,
            status=args.status,
            results_summary=summary_data,
        )
        if finalized:
            print(f"✓ Finalized {args.run_id}: status={finalized.status}, end_time={finalized.end_time}")
            return 0
        else:
            print(f"❌ Failed to find or finalize run {args.run_id}")
            return 1

    if args.command == "status":
        print(f"=== Experiment Tracking Status: {config.project_name or config.root_dir.name} ===")
        print(f"Root: {config.root_dir}")
        running = find_running_snapshot(config)
        if running:
            print(f"\n⚠️  RUNNING EXPERIMENT IN-FLIGHT:")
            print(f"   ID: {running.run_id}")
            print(f"   Description: {running.description}")
            print(f"   Started: {running.start_time}")
        else:
            print("\nNo experiment currently marked RUNNING.")

        if config.readme_file.exists():
            exps, rounds = parse_reviews_readme(config.readme_file)
            print(f"\nIndexed Experiments ({len(exps)}):")
            for e in exps:
                print(f"  - {e.experiment}: {e.subject} ({e.rounds})")
            print(f"Total review rounds: {len(rounds)}")

        if config.tracker_file.exists():
            issues = parse_tracker(config.tracker_file)
            open_issues = [i for i in issues if i.status.lower() in OPEN_STATUSES]
            print(f"Tracker Issues: {len(issues)} total ({len(open_issues)} open)")
            for i in open_issues[:5]:
                print(f"  - [{i.severity}] {i.issue_id}: {i.title} ({i.status})")
            if len(open_issues) > 5:
                print(f"    ... and {len(open_issues) - 5} more")
        return 0

    if args.command == "serve":
        if args.rebuild or not (config.reviews_dir / "IDEA_GRAPH.html").exists():
            print("Rebuilding review graph before serving...")
            build_command(args, config)
        serve_dashboard(config, port=args.port, open_browser=args.open)
        return 0

    # Default command: build
    return build_command(args, config)


if __name__ == "__main__":
    sys.exit(main())
