from __future__ import annotations

import copy
import hashlib
import html
import json
import re
from pathlib import Path
from typing import Any

from .parsers.files import href_for_path_from_base

HTML_TEMPLATE_PATH = Path(__file__).parent / "templates" / "review_graph_template.html"
HTML_EXPORT_PREVIEW_DIR = "previews"

_PREVIEW_PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>__PAGE_TITLE__</title>
  <style>
    :root {
      --bg: #f8fafc;
      --panel: #ffffff;
      --ink: #111827;
      --muted: #64748b;
      --line: #cbd5e1;
      --accent: #2563eb;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      letter-spacing: 0;
    }
    header {
      position: sticky;
      top: 0;
      z-index: 1;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
      padding: 14px 18px;
    }
    h1 {
      margin: 0;
      font-size: 18px;
      line-height: 1.25;
      overflow-wrap: anywhere;
    }
    .meta {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      margin-top: 8px;
      color: var(--muted);
      font-size: 13px;
    }
    .toggle-group {
      display: inline-flex;
      border: 1px solid var(--line);
      border-radius: 6px;
      overflow: hidden;
      background: #ffffff;
    }
    .toggle-group button {
      border: 0;
      border-right: 1px solid var(--line);
      min-height: 30px;
      padding: 5px 10px;
      background: #ffffff;
      color: #334155;
      cursor: pointer;
      font: inherit;
      font-size: 12px;
      font-weight: 650;
    }
    .toggle-group button:last-child { border-right: 0; }
    .toggle-group button.active {
      background: #eff6ff;
      color: #1d4ed8;
    }
    .raw-link {
      color: #1d4ed8;
      font-weight: 650;
      text-decoration: none;
    }
    .raw-link:hover { text-decoration: underline; }
    main {
      padding: 16px 18px 28px;
      max-width: 1120px;
    }
    pre {
      margin: 0;
      border: 1px solid var(--line);
      border-radius: 7px;
      background: #0f172a;
      color: #e5e7eb;
      padding: 14px 16px;
      overflow-x: auto;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 13px;
      line-height: 1.55;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .rendered-markdown {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #ffffff;
      padding: 20px 24px;
      font-size: 14px;
      line-height: 1.6;
    }
    .rendered-markdown h1, .rendered-markdown h2, .rendered-markdown h3 {
      color: #0f172a;
      margin: 1.3em 0 0.45em;
      line-height: 1.3;
    }
    .rendered-markdown h1:first-child, .rendered-markdown h2:first-child { margin-top: 0; }
    .rendered-markdown p { margin: 0.6em 0; }
    .rendered-markdown code {
      background: #f1f5f9;
      padding: 2px 5px;
      border-radius: 4px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, monospace;
      font-size: 12px;
    }
    .num-hl {
      color: #38bdf8;
      font-weight: 700;
    }
    .num-hl-good {
      color: #4ade80;
      font-weight: 700;
    }
    .num-hl-bad {
      color: #f87171;
      font-weight: 700;
    }
  </style>
</head>
<body>
  <header>
    <h1>__TITLE__</h1>
    <div class="meta">
      <span>__META_SUMMARY__</span>
      __TOGGLE_BUTTONS__
      __RAW_LINK__
    </div>
  </header>
  <main>
    __MAIN_CONTENT__
  </main>
  <script>
    function showTab(name) {
      document.querySelectorAll('.tab-content').forEach(el => el.style.display = 'none');
      document.querySelectorAll('.toggle-group button').forEach(el => el.classList.remove('active'));
      const activeEl = document.getElementById('tab-' + name);
      if (activeEl) activeEl.style.display = 'block';
      const btn = document.getElementById('btn-' + name);
      if (btn) btn.classList.add('active');
    }
  </script>
</body>
</html>"""


def _highlight_json_numbers(escaped: str) -> str:
    def repl(m: re.Match) -> str:
        key = m.group(1)
        colon = m.group(2)
        val = m.group(3)
        try:
            num = float(val)
            if "fail" in key.lower() or "error" in key.lower() or "oor" in key.lower():
                cls = "num-hl-bad" if num > 0 else "num-hl-good"
            elif "success" in key.lower() or "reward" in key.lower() or "return" in key.lower():
                cls = "num-hl-good" if num > 0 else "num-hl"
            else:
                cls = "num-hl"
        except ValueError:
            cls = "num-hl"
        return f'{key}{colon}<span class="{cls}">{val}</span>'

    return re.sub(r'(&quot;[^&]+&quot;)(\s*:\s*)(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)', repl, escaped)


def _render_simple_markdown(raw_md: str) -> str:
    lines = raw_md.splitlines()
    out: list[str] = []
    in_code = False
    for line in lines:
        if line.startswith("```"):
            if in_code:
                out.append("</pre>")
                in_code = False
            else:
                out.append("<pre><code>")
                in_code = True
            continue
        if in_code:
            out.append(html.escape(line))
            continue
        if line.startswith("# "):
            out.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            out.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("### "):
            out.append(f"<h3>{html.escape(line[4:])}</h3>")
        elif line.startswith("- "):
            out.append(f"<li>{html.escape(line[2:])}</li>")
        elif line.strip():
            out.append(f"<p>{html.escape(line)}</p>")
    if in_code:
        out.append("</pre>")
    return "\n".join(out)


def render_html(data: dict[str, Any], title: str, template_path: Path | None = None) -> str:
    """Render the full interactive HTML review graph."""
    tmpl_path = template_path or HTML_TEMPLATE_PATH
    if not tmpl_path.exists():
        raise FileNotFoundError(f"Review graph HTML template not found at {tmpl_path}")
    tmpl = tmpl_path.read_text(encoding="utf-8")
    json_blob = json.dumps(data, indent=2, ensure_ascii=False)
    rendered = tmpl.replace("__TITLE__", html.escape(title))
    rendered = rendered.replace('"__GRAPH_DATA__"', json_blob)
    rendered = rendered.replace("__GRAPH_DATA__", json_blob)
    return rendered


def data_with_links(data: dict[str, Any], base_dir: Path, root: Path, reviews_dir_prefix: str = "reports/reviews") -> dict[str, Any]:
    """Clone graph data and update node paths and hrefs relative to base_dir."""
    cloned = copy.deepcopy(data)
    for node in cloned.get("nodes", []):
        raw_path = node.get("path")
        if raw_path:
            node["href"] = href_for_path_from_base(raw_path, base_dir, root, reviews_dir_prefix)
    return cloned


def write_html_export(
    data: dict[str, Any],
    output_dir: Path,
    title: str,
    root: Path,
    reviews_dir_prefix: str = "reports/reviews",
    template_path: Path | None = None,
) -> None:
    """Write static folder export with index.html and standalone preview pages."""
    output_dir.mkdir(parents=True, exist_ok=True)
    previews_dir = output_dir / HTML_EXPORT_PREVIEW_DIR
    previews_dir.mkdir(parents=True, exist_ok=True)

    # Export standalone preview files
    data_for_export = data_with_links(data, output_dir, root, reviews_dir_prefix)

    for node in data_for_export.get("nodes", []):
        raw_path = node.get("path")
        preview = node.get("preview")
        if not raw_path or not preview or not preview.get("available"):
            continue

        h = hashlib.sha1(raw_path.encode("utf-8")).hexdigest()[:10]
        safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", raw_path.replace("/", "_"))[:48]
        preview_filename = f"{safe_name}_{h}.html"
        preview_page_path = previews_dir / preview_filename
        node["previewUrl"] = f"{HTML_EXPORT_PREVIEW_DIR}/{preview_filename}"

        text_content = preview.get("text", "")
        raw_link_html = ""
        if node.get("href"):
            raw_link_html = f'<a class="raw-link" href="../{node["href"]}" target="_blank">Raw file</a>'

        toggle_buttons = ""
        main_content = ""
        fmt = preview.get("format", "text")

        if fmt == "markdown":
            toggle_buttons = (
                '<div class="toggle-group">'
                '<button id="btn-rendered" class="active" onclick="showTab(\'rendered\')">Rendered</button>'
                '<button id="btn-source" onclick="showTab(\'source\')">Source</button>'
                '</div>'
            )
            main_content = (
                f'<div id="tab-rendered" class="tab-content rendered-markdown">{_render_simple_markdown(text_content)}</div>'
                f'<div id="tab-source" class="tab-content" style="display:none;"><pre><code>{html.escape(text_content)}</code></pre></div>'
            )
        elif fmt == "json":
            highlighted = _highlight_json_numbers(html.escape(text_content))
            main_content = f'<pre><code>{highlighted}</code></pre>'
        else:
            main_content = f'<pre><code>{html.escape(text_content)}</code></pre>'

        meta_summary = f"{preview.get('kind', 'file')} | {preview.get('sizeBytes', 0):,} bytes"
        page_html = _PREVIEW_PAGE_TEMPLATE.replace("__PAGE_TITLE__", html.escape(f"{Path(raw_path).name} preview"))
        page_html = page_html.replace("__TITLE__", html.escape(raw_path))
        page_html = page_html.replace("__META_SUMMARY__", html.escape(meta_summary))
        page_html = page_html.replace("__TOGGLE_BUTTONS__", toggle_buttons)
        page_html = page_html.replace("__RAW_LINK__", raw_link_html)
        page_html = page_html.replace("__MAIN_CONTENT__", main_content)

        preview_page_path.write_text(page_html, encoding="utf-8")

    index_html = render_html(data_for_export, title, template_path)
    (output_dir / "index.html").write_text(index_html, encoding="utf-8")


def write_output(
    content: str,
    output_path: Path,
) -> None:
    """Write text content to file, creating parent directories if needed."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
