from __future__ import annotations

import functools
import http.server
import socketserver
import webbrowser
from pathlib import Path

from .config import ProjectConfig


def serve_dashboard(
    config: ProjectConfig,
    port: int = 8080,
    open_browser: bool = False,
    html_file: Path | None = None,
) -> None:
    """Serve the generated IDEA_GRAPH.html review explorer via local HTTP."""
    target_dir = config.reviews_dir if (config.reviews_dir / "IDEA_GRAPH.html").exists() else config.root_dir

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(target_dir))

    class ReusableTCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    with ReusableTCPServer(("", port), handler) as httpd:
        url = f"http://localhost:{port}/IDEA_GRAPH.html"
        print(f"\n🚀 Experiment Tracker Dashboard running at:")
        print(f"   {url}")
        print(f"   Serving directory: {target_dir}")
        print("   Press Ctrl+C to stop.\n")

        if open_browser:
            webbrowser.open(url)

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")
