from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

_HEADER_RE = re.compile(r"^([0-9a-f]{40})\|(.+?)\|(.*)$")
_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})(?:\s+(\d{2}:\d{2}))?")

_SKIP_RE = re.compile(r"^reports/reviews/|\.html$|^CHANGELOG\.md$|^changelog\.md$|^TRACKER\.md$|^reports/reviews/README\.md$")
_CODE_RE = re.compile(r"\.(py|sh|yaml|yml|json|toml|rs|cpp|c|cu|h)$|^scripts/|^configs/|^src/")


@dataclass(frozen=True)
class GitCommit:
    sha: str
    date: datetime
    subject: str
    changed_files: tuple[str, ...]


def parse_round_date(date_str: str) -> datetime | None:
    m = _DATE_RE.search(date_str.strip())
    if not m:
        return None
    time_part = m.group(2) or "23:59"
    try:
        return datetime.strptime(f"{m.group(1)} {time_part}", "%Y-%m-%d %H:%M")
    except ValueError:
        return None


def run_git_command(args: list[str], root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        args,
        cwd=root,
        capture_output=True,
        text=True,
    )


def git_short_hash(root: Path) -> str:
    res = run_git_command(["git", "rev-parse", "--short", "HEAD"], root)
    return res.stdout.strip() if res.returncode == 0 else "unknown"


def git_diff_stat(root: Path) -> str:
    res = run_git_command(["git", "diff", "--stat"], root)
    return res.stdout.strip() if res.returncode == 0 else ""


def get_current_git_ref(root: Path) -> str:
    res = run_git_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], root)
    branch = res.stdout.strip() if res.returncode == 0 else ""
    if branch and branch != "HEAD":
        return branch
    res_full = run_git_command(["git", "rev-parse", "HEAD"], root)
    return res_full.stdout.strip() if res_full.returncode == 0 else "main"


def load_commits(root: Path) -> list[GitCommit]:
    """Load all non-merge commits from git log with code/config changed files only."""
    result = run_git_command(
        ["git", "log", "--format=%H|%aI|%s", "--name-only", "--no-merges", "--diff-filter=ACMR"],
        root,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return []

    commits: list[GitCommit] = []
    sha: str | None = None
    date: datetime | None = None
    subject = ""
    files: list[str] = []

    for line in result.stdout.splitlines():
        m = _HEADER_RE.match(line)
        if m:
            if sha is not None:
                commits.append(GitCommit(sha=sha, date=date, subject=subject, changed_files=tuple(files)))
            sha = m.group(1)
            try:
                date = datetime.fromisoformat(m.group(2)).astimezone(timezone.utc).replace(tzinfo=None)
            except Exception:
                date = datetime.now()
            subject = m.group(3)
            files = []
        elif line.strip() and sha is not None:
            path = line.strip()
            if _CODE_RE.search(path) and not _SKIP_RE.search(path):
                files.append(path)

    if sha is not None:
        commits.append(GitCommit(sha=sha, date=date, subject=subject, changed_files=tuple(files)))

    return commits


def commits_for_window(
    commits: list[GitCommit],
    since: datetime | None,
    until: datetime | None,
) -> list[GitCommit]:
    """Return commits with date in (since, until], both bounds optional."""
    return [
        c for c in commits
        if (since is None or c.date > since) and (until is None or c.date <= until)
    ]
