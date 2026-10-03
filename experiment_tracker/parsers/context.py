from __future__ import annotations

import re
from pathlib import Path

from ..models import RoundContext
from .files import extract_paths

CONTEXT_FIELD_RE = re.compile(
    r"^\s*(?:[-*]\s*)?(?:\*\*)?(?P<key>Trigger|Focus|Experiment|Round|Date|Git(?: state)?|Reviewers|Outcome|Issues opened|Issues resolved)(?:\*\*)?:(?:\*\*)?[ \t]*(?P<value>.+)$",
    re.IGNORECASE,
)


def parse_context_file(path: Path, reviews_dir_prefix: str = "reports/reviews") -> RoundContext:
    """Parse one round's CONTEXT.md into a RoundContext record."""
    if not path.exists():
        round_dir = path.parent
        exp_dir = round_dir.parent
        return RoundContext(
            experiment=exp_dir.name,
            round_name=round_dir.name,
            trigger="",
            focus="",
            what_changed="",
            evidence_summary="",
            open_issues_before="",
        )

    raw = path.read_text(encoding="utf-8", errors="replace")
    lines = raw.splitlines()

    fields: dict[str, str] = {}
    for line in lines[:30]:
        m = CONTEXT_FIELD_RE.match(line)
        if m:
            clean_val = re.sub(r"^[*_`\s]+|[*_`\s]+$", "", m.group("value").strip())
            fields[m.group("key").lower()] = clean_val

    round_dir = path.parent
    exp_dir = round_dir.parent
    experiment = fields.get("experiment", exp_dir.name)
    round_raw = fields.get("round", "")
    if re.fullmatch(r"\d+", round_raw):
        round_name = f"round_{round_raw.zfill(3)}"
    elif round_raw and not round_raw.startswith("round_"):
        round_name = f"round_{round_raw}"
    elif round_raw:
        round_name = round_raw
    else:
        round_name = round_dir.name

    trigger = fields.get("trigger", "")
    focus = fields.get("focus", "")
    reviewers = fields.get("reviewers", "")
    outcome = fields.get("outcome", "")
    issues_opened = fields.get("issues opened", "")
    issues_resolved = fields.get("issues resolved", "")

    sections: dict[str, list[str]] = {}
    current_section = ""
    for line in lines:
        m2 = re.match(r"^##\s+(.+)$", line)
        if m2:
            current_section = m2.group(1).strip()
            sections[current_section] = []
            continue
        if current_section:
            sections[current_section].append(line)

    def get_section(*keywords: str) -> str:
        for key in sections:
            if any(kw.lower() in key.lower() for kw in keywords):
                return "\n".join(sections[key]).strip()
        return ""

    what_changed = get_section("what changed", "changes since", "changed since")
    evidence_summary = get_section("evidence available", "results summary", "evidence", "findings")
    open_before = get_section("open issue count", "open issues entering", "open issues before")

    issue_refs = tuple(dict.fromkeys(re.findall(r"\bI-\d{3,}\b", raw)))
    file_paths = tuple(dict.fromkeys(extract_paths(raw, reviews_dir_prefix)))

    return RoundContext(
        experiment=experiment,
        round_name=round_name,
        trigger=trigger,
        focus=focus,
        what_changed=what_changed,
        evidence_summary=evidence_summary,
        open_issues_before=open_before,
        issue_refs=issue_refs,
        file_paths=file_paths,
        reviewers=reviewers,
        outcome=outcome,
        issues_opened=issues_opened,
        issues_resolved=issues_resolved,
    )


def parse_all_contexts(reviews_dir: Path, reviews_dir_prefix: str = "reports/reviews") -> dict[tuple[str, str], RoundContext]:
    """Walk experiments/*/round_*/CONTEXT.md and index by (experiment, round_name)."""
    result: dict[tuple[str, str], RoundContext] = {}
    experiments_dir = reviews_dir / "experiments"
    if not experiments_dir.is_dir():
        return result
    for exp_dir in sorted(experiments_dir.iterdir()):
        if not exp_dir.is_dir():
            continue
        for round_dir in sorted(exp_dir.iterdir()):
            if not round_dir.is_dir():
                continue
            context_path = round_dir / "CONTEXT.md"
            if context_path.exists():
                ctx = parse_context_file(context_path, reviews_dir_prefix)
                result[(ctx.experiment, ctx.round_name)] = ctx
    return result
