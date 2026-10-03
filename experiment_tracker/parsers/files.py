from __future__ import annotations

import glob as glob_mod
import json
import os
import re
from pathlib import Path

PREVIEW_SUFFIXES = {".json", ".jsonl", ".md", ".txt", ".yaml", ".yml", ".py", ".sh", ".toml", ".csv"}
MAX_FILE_PREVIEW_CHARS = 10_000


def looks_like_path(text: str) -> bool:
    """Keep only strings that look like repo files or review artifacts."""
    stripped = text.strip()
    if any(char in stripped for char in ' "\'()<>'):
        return False
    if stripped.startswith(("runs/", "reports/", "scripts/", "configs/", "logs/", "artifacts/", "experiments/")):
        return True
    return bool(re.search(r"\.(py|sh|jsonl|json|yaml|yml|md|zip|txt|toml|csv)$", stripped))


def extract_backtick_paths(text: str) -> list[str]:
    """Extract paths that were explicitly marked as inline code."""
    return [item.strip() for item in re.findall(r"`([^`]+)`", text) if looks_like_path(item)]


def normalize_path(path: str, reviews_dir_prefix: str = "reports/reviews") -> str:
    """Normalize short review-local paths so graph links are consistent."""
    cleaned = path.strip().strip("`").rstrip(".,;:")
    cleaned = re.sub(r"/+$", "", cleaned)
    if cleaned.startswith("experiments/"):
        return f"{reviews_dir_prefix}/{cleaned}"
    if re.match(r"experiment_\d{3}/", cleaned):
        return f"{reviews_dir_prefix}/experiments/{cleaned}"
    if cleaned in {"README.md", "TRACKER.md", "IDEA_GRAPH.md", "IDEA_GRAPH.html"}:
        return f"{reviews_dir_prefix}/{cleaned}"
    return cleaned


def extract_paths(text: str, reviews_dir_prefix: str = "reports/reviews") -> list[str]:
    """Find referenced files in free text from reviews, issues, and changelog."""
    paths = extract_backtick_paths(text)
    regex_paths = re.findall(
        r"(?<![\w-])(?:runs|reports|scripts|configs|artifacts|logs)/[A-Za-z0-9_./{}*,=-]+|"
        r"(?<![\w-])[A-Za-z0-9_./-]+\.(?:py|sh|jsonl|json|yaml|yml|md|zip|toml|csv)",
        text,
    )
    for path in regex_paths:
        cleaned = path.rstrip(".,;:)")
        if looks_like_path(cleaned) and cleaned not in paths:
            paths.append(cleaned)
    return [normalize_path(p, reviews_dir_prefix) for p in paths]


def expand_brace_glob(path: str, root: Path, reviews_dir_prefix: str = "reports/reviews") -> list[Path]:
    """Expand shell-style {a,b} brace groups and * globs into matching local Paths."""
    normalized = normalize_path(path, reviews_dir_prefix)
    brace_re = re.compile(r"\{([^{}]+)\}")
    patterns = [normalized]
    while True:
        new_patterns: list[str] = []
        changed = False
        for pat in patterns:
            m = brace_re.search(pat)
            if m:
                changed = True
                for option in m.group(1).split(","):
                    new_patterns.append(pat[: m.start()] + option.strip() + pat[m.end():])
            else:
                new_patterns.append(pat)
        patterns = new_patterns
        if not changed:
            break

    results: list[Path] = []
    for pat in patterns:
        for hit in sorted(glob_mod.glob(str(root / pat))):
            candidate = Path(hit).resolve()
            try:
                candidate.relative_to(root.resolve())
                results.append(candidate)
            except ValueError:
                pass
    seen: set[Path] = set()
    unique: list[Path] = []
    for p in results:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


def href_for_path_from_base(path: str, base_dir: Path, root: Path, reviews_dir_prefix: str = "reports/reviews") -> str:
    """Convert a repo-relative artifact path into a link from an output folder."""
    if not path:
        return ""
    root = root.resolve()
    base_dir = base_dir.resolve()
    if "*" in path or "{" in path or "}" in path:
        matches = expand_brace_glob(path, root, reviews_dir_prefix)
        if not matches:
            return ""
        return Path(os.path.relpath(matches[0], base_dir)).as_posix()
    normalized = normalize_path(path, reviews_dir_prefix)
    if normalized.startswith(("reports/", "runs/", "scripts/", "configs/", "artifacts/", "logs/")) or re.search(
        r"\.(py|sh|jsonl|json|yaml|yml|md|zip|txt|toml|csv)$", normalized
    ):
        target = (root / normalized).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            return ""
        return Path(os.path.relpath(target, base_dir)).as_posix()
    return ""


def href_for_path(path: str, root: Path, reviews_dir_prefix: str = "reports/reviews") -> str:
    """Convert a repo-relative artifact path into a link from reviews directory."""
    return href_for_path_from_base(path, root / reviews_dir_prefix, root, reviews_dir_prefix)


def local_file_for_path(path: str, root: Path, reviews_dir_prefix: str = "reports/reviews") -> Path | None:
    """Resolve a graph path to a local repo file when it is safe to preview."""
    if not path or "*" in path or "{" in path or "}" in path:
        return None
    root = root.resolve()
    candidate = (root / normalize_path(path, reviews_dir_prefix)).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def file_preview(path: str, root: Path, reviews_dir_prefix: str = "reports/reviews") -> dict[str, object]:
    """Return a small text preview payload for file nodes in the HTML explorer."""
    root = root.resolve()
    if "*" in path or "{" in path or "}" in path:
        matches = expand_brace_glob(path, root, reviews_dir_prefix)
        if not matches:
            return {"available": False, "reason": "glob matches no local files"}
        if len(matches) == 1:
            return file_preview(str(matches[0].relative_to(root)), root, reviews_dir_prefix)
        lines = [f"{len(matches)} files matched:\n"] + [f"- {m.relative_to(root)}" for m in matches]
        return {
            "available": True,
            "kind": f"{len(matches)} files",
            "format": "text",
            "text": "\n".join(lines),
            "truncated": False,
            "sizeBytes": sum(m.stat().st_size for m in matches),
        }

    local_path = local_file_for_path(path, root, reviews_dir_prefix)
    if local_path is None:
        return {"available": False, "reason": "not a local text file path"}
    suffix = local_path.suffix.lower()
    if suffix not in PREVIEW_SUFFIXES:
        return {"available": False, "reason": f"{suffix or 'file'} preview is not supported"}

    raw_text = local_path.read_text(encoding="utf-8", errors="replace")
    preview_format = {
        ".md": "markdown",
        ".json": "json",
        ".jsonl": "jsonl",
        ".txt": "text",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".py": "python",
        ".sh": "shell",
        ".toml": "toml",
        ".csv": "csv",
    }.get(suffix, "text")
    kind = "markdown" if suffix == ".md" else suffix.removeprefix(".") or "text"
    if suffix == ".json":
        try:
            raw_text = json.dumps(json.loads(raw_text), indent=2, ensure_ascii=False)
            kind = "pretty json"
        except json.JSONDecodeError:
            kind = "json text"

    truncated = len(raw_text) > MAX_FILE_PREVIEW_CHARS
    preview_text = raw_text[:MAX_FILE_PREVIEW_CHARS]
    if truncated:
        preview_text = preview_text.rstrip() + "\n\n... preview truncated ..."
    return {
        "available": True,
        "kind": kind,
        "format": preview_format,
        "text": preview_text,
        "truncated": truncated,
        "sizeBytes": local_path.stat().st_size,
    }
