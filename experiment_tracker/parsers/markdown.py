from __future__ import annotations

import re
from pathlib import Path

from ..models import ChangeEntry, Experiment, Issue, Round
from .files import extract_paths, normalize_path


def split_table_row(line: str) -> list[str]:
    """Split a markdown table row while keeping pipes inside inline code."""
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]

    cells: list[str] = []
    current: list[str] = []
    in_code = False
    escaped = False
    for char in stripped:
        if escaped:
            current.append(char)
            escaped = False
            continue
        if char == "\\":
            current.append(char)
            escaped = True
            continue
        if char == "`":
            in_code = not in_code
            current.append(char)
            continue
        if char == "|" and not in_code:
            cells.append("".join(current).strip())
            current = []
            continue
        current.append(char)
    cells.append("".join(current).strip())
    return cells


def is_separator_row(cells: list[str]) -> bool:
    """Return true for markdown separator rows like | --- | :---: |."""
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def parse_markdown_tables(path: Path) -> list[tuple[list[str], list[dict[str, str]]]]:
    """Return every markdown table as (header, rows) from a source file."""
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    tables: list[tuple[list[str], list[dict[str, str]]]] = []
    i = 0
    while i < len(lines):
        if not lines[i].lstrip().startswith("|"):
            i += 1
            continue
        header = split_table_row(lines[i])
        if i + 1 >= len(lines):
            i += 1
            continue
        separator = split_table_row(lines[i + 1])
        if not is_separator_row(separator):
            i += 1
            continue
        rows: list[dict[str, str]] = []
        i += 2
        while i < len(lines) and lines[i].lstrip().startswith("|"):
            cells = split_table_row(lines[i])
            if len(cells) < len(header):
                cells += [""] * (len(header) - len(cells))
            rows.append(dict(zip(header, cells[: len(header)])))
            i += 1
        tables.append((header, rows))
    return tables


def find_table(
    tables: list[tuple[list[str], list[dict[str, str]]]], required: set[str]
) -> list[dict[str, str]]:
    """Pick the first table that contains the required column names."""
    for header, rows in tables:
        if required.issubset(set(header)):
            return rows
    return []


def parse_reviews_readme(path: Path) -> tuple[list[Experiment], list[Round]]:
    """Parse the review index into experiment-level and round-level records."""
    tables = parse_markdown_tables(path)
    experiment_rows = find_table(tables, {"Experiment", "Subject", "Evidence base", "Rounds"})
    round_rows = find_table(tables, {"Experiment", "Round", "Date", "Focus", "Trigger", "Report"})

    experiments = [
        Experiment(
            experiment=row["Experiment"].strip(),
            subject=row["Subject"].strip(),
            evidence_base=row["Evidence base"].strip(),
            rounds=row["Rounds"].strip(),
            open_issues=row.get("Open issues after latest round", row.get("Open issues", "")).strip(),
        )
        for row in experiment_rows
        if row.get("Experiment", "").strip()
    ]

    rounds = [
        Round(
            experiment=row["Experiment"].strip(),
            round_name=row["Round"].strip(),
            date=row["Date"].strip(),
            focus=row["Focus"].strip(),
            trigger=row["Trigger"].strip(),
            report=row["Report"].strip(),
            open_issues=row.get("Open issues after round", row.get("Open issues", "")).strip(),
        )
        for row in round_rows
        if row.get("Experiment", "").strip() and row.get("Round", "").strip()
    ]

    return experiments, rounds


def parse_tracker(path: Path) -> list[Issue]:
    """Parse open, resolved, and historical issues from TRACKER.md."""
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    issues: list[Issue] = []
    current_section = "Tracker"
    i = 0
    while i < len(lines):
        line = lines[i]
        section_match = re.match(r"^##\s+(.+)$", line)
        if section_match:
            current_section = section_match.group(1).strip()
            i += 1
            continue

        if not line.lstrip().startswith("|"):
            i += 1
            continue

        header = split_table_row(line)
        if i + 1 >= len(lines):
            i += 1
            continue
        separator = split_table_row(lines[i + 1])
        if not is_separator_row(separator):
            i += 1
            continue

        required = {"ID", "Sev", "Summary", "Found", "Status"}
        if not required.issubset(set(header)):
            i += 1
            continue

        i += 2
        while i < len(lines) and lines[i].lstrip().startswith("|"):
            cells = split_table_row(lines[i])
            if len(cells) < len(header):
                cells += [""] * (len(header) - len(cells))
            row = dict(zip(header, cells[: len(header)]))
            issue_id = row.get("ID", "").strip()
            if issue_id and re.match(r"^I-\d{3,}", issue_id):
                found = row.get("Found", "").strip()
                # Parse experiment and round if slash-separated
                if "/" in found:
                    parts = [p.strip() for p in found.split("/") if p.strip()]
                    exp = next((p for p in parts if p.startswith("experiment_")), "")
                    rnd = next((p for p in parts if p.startswith("round_")), parts[-1])
                else:
                    exp = ""
                    rnd = found

                evidence = row.get("Evidence", row.get("Notes", "")).strip()
                next_step = row.get("Next Step", row.get("Next step", row.get("Resolved", ""))).strip()

                issues.append(
                    Issue(
                        issue_id=issue_id,
                        severity=row.get("Sev", "P2").strip(),
                        status=row.get("Status", "open").strip().lower(),
                        experiment=exp,
                        round_name=rnd,
                        title=row.get("Summary", "").strip(),
                        evidence=evidence,
                        next_step=next_step,
                        source_section=current_section,
                    )
                )
            i += 1
    return issues


def parse_changelog(path: Path, reviews_dir_prefix: str = "reports/reviews") -> list[ChangeEntry]:
    """Parse changelog into change entries with linked experiment, round, and file refs."""
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    entries: list[ChangeEntry] = []
    current_title = ""
    current_timestamp = ""
    body_lines: list[str] = []

    def commit_entry() -> None:
        if not current_title:
            return
        body = "\n".join(body_lines).strip()
        combined_text = f"{current_title}\n{body}".replace("`", "")
        files = tuple(dict.fromkeys(extract_paths(body, reviews_dir_prefix)))
        experiments = tuple(dict.fromkeys(re.findall(r"\bexperiment_\d{3}\b", combined_text)))
        rounds_matches = re.findall(r"\b(experiment_\d{3})[ /]+(round_\d{3})\b", combined_text)
        round_tuples = tuple(dict.fromkeys((exp, rnd) for exp, rnd in rounds_matches))

        entries.append(
            ChangeEntry(
                timestamp=current_timestamp,
                title=current_title,
                body=body,
                files=files,
                experiments=experiments,
                rounds=round_tuples,
            )
        )

    for line in lines:
        heading_match = re.match(r"^##\s+(?:\[(?P<ts_bracket>[^\]]+)\]\s*--\s*)?(?P<title>.+)$", line)
        date_heading_match = re.match(r"^##\s+(?P<date>\d{4}-\d{2}-\d{2})(?:\s*--\s*(?P<extra>.*))?$", line)

        if heading_match:
            commit_entry()
            current_timestamp = (heading_match.group("ts_bracket") or "").strip()
            current_title = heading_match.group("title").strip()
            body_lines = []
        elif date_heading_match:
            commit_entry()
            current_timestamp = date_heading_match.group("date").strip()
            extra = date_heading_match.group("extra") or ""
            current_title = extra.strip() or f"Changes on {current_timestamp}"
            body_lines = []
        else:
            if current_title:
                body_lines.append(line)

    commit_entry()
    return entries
