import html
import json
import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs, unquote, urlparse

from .dashboard_read_model import DashboardReadModel


def _json_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False).encode("utf-8")


def _safe_link(label: str, target: str) -> str:
    target = html.unescape(target)
    if target.startswith(("http://", "https://", "/")):
        return f'<a href="{html.escape(target, quote=True)}" target="_blank" rel="noreferrer">{label}</a>'
    return label


def render_markdown(source: str) -> str:
    """Small safe Markdown subset; raw HTML and script-like URLs are escaped."""
    lines = source.replace("\r\n", "\n").split("\n")
    output: list[str] = []
    in_code = False
    code_lines: list[str] = []
    paragraph: list[str] = []

    def inline(value: str) -> str:
        value = html.escape(value, quote=True)
        value = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", lambda match: _safe_link(match.group(1), match.group(2)), value)
        value = re.sub(r"`([^`]+)`", r"<code>\1</code>", value)
        value = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", value)
        value = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", value)
        return value

    def flush_paragraph() -> None:
        if paragraph:
            output.append("<p>" + "<br>".join(inline(item) for item in paragraph) + "</p>")
            paragraph.clear()

    for line in lines:
        if line.startswith("```"):
            flush_paragraph()
            if in_code:
                output.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
                code_lines.clear()
            in_code = not in_code
            continue
        if in_code:
            code_lines.append(line)
            continue
        if not line.strip():
            flush_paragraph()
            continue
        heading = re.match(r"^(#{1,3})\s+(.+)$", line)
        if heading:
            flush_paragraph()
            level = len(heading.group(1))
            output.append(f"<h{level}>" + inline(heading.group(2)) + f"</h{level}>")
            continue
        bullet = re.match(r"^\s*[-*]\s+(.+)$", line)
        if bullet:
            flush_paragraph()
            if not output or not output[-1].startswith("<ul>"):
                output.append("<ul>")
            output[-1] += "<li>" + inline(bullet.group(1)) + "</li>"
            continue
        if output and output[-1].startswith("<ul>") and not line.lstrip().startswith(("-", "*")):
            output[-1] += "</ul>"
        paragraph.append(line)
    flush_paragraph()
    if output and output[-1].startswith("<ul>") and not output[-1].endswith("</ul>"):
        output[-1] += "</ul>"
    if in_code:
        output.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
    return "\n".join(output)


def _find_browser_app() -> str | None:
    candidates = [
        Path(os.environ.get("PROGRAMFILES", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(os.environ.get("PROGRAMFILES", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return shutil.which("msedge") or shutil.which("chrome")


def open_desktop_window(url: str, profile_root: str | Path | None = None) -> subprocess.Popen | None:
    executable = _find_browser_app()
    if executable:
        profile = Path(profile_root) if profile_root else Path(
            os.environ.get("LOCALAPPDATA", tempfile.gettempdir())
        ) / "TechChancellor" / "BrowserProfile"
        profile = profile.resolve()
        profile.mkdir(parents=True, exist_ok=True)
        return subprocess.Popen(
            [
                executable,
                f"--app={url}",
                f"--user-data-dir={profile}",
                "--no-first-run",
                "--disable-extensions",
            ],
            close_fds=True,
        )
    webbrowser.open(url)
    return None


def open_in_obsidian(root: Path) -> bool:
    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Obsidian" / "Obsidian.exe",
        Path(os.environ.get("PROGRAMFILES", "")) / "Obsidian" / "Obsidian.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Obsidian" / "Obsidian.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Obsidian" / "Obsidian.exe",
    ]
    executable = next((path for path in candidates if path.is_file()), None)
    if not executable:
        return False
    subprocess.Popen([str(executable), str(root)], close_fds=True)
    return True


class _DashboardHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class DashboardServer:
    def __init__(self, root: str | Path, host: str = "127.0.0.1", port: int = 0):
        self.root = Path(root).resolve()
        self.host = host
        self.port = port
        self.model = DashboardReadModel(self.root)
        self.httpd: _DashboardHTTPServer | None = None
        self.thread: Thread | None = None

    def start(self) -> tuple[_DashboardHTTPServer, str]:
        model = self.model
        asset_root = Path(__file__).with_name("dashboard_assets")

        class Handler(BaseHTTPRequestHandler):
            server_version = "TechChancellorDashboard/0.8"
            static_assets = {
                "app.css": "text/css; charset=utf-8",
                "app.js": "text/javascript; charset=utf-8",
                "advisor-studio-v2.png": "image/png",
                "capability-studio-v2.png": "image/png",
            }

            def log_message(self, format: str, *args: object) -> None:
                return

            def _send(self, status: int, body: bytes, content_type: str) -> None:
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def _api(self, payload: object, status: int = 200) -> None:
                self._send(status, _json_bytes(payload), "application/json; charset=utf-8")

            def do_GET(self) -> None:
                parsed = urlparse(self.path)
                path = unquote(parsed.path)
                try:
                    if path in {"/", "/index.html"}:
                        self._send(200, (asset_root / "index.html").read_bytes(), "text/html; charset=utf-8")
                        return
                    if path in {"/app.css", "/app.js"}:
                        path = "/assets/" + path.rsplit("/", 1)[1]
                    if path.startswith("/assets/"):
                        name = path.removeprefix("/assets/")
                        if name in self.static_assets and Path(name).name == name:
                            self._send(200, (asset_root / name).read_bytes(), self.static_assets[name])
                            return
                        return
                    if path == "/api/summary":
                        self._api(model.snapshot())
                        return
                    if path == "/api/health":
                        self._api(model.snapshot().get("health", {}))
                        return
                    if path == "/api/capabilities":
                        params = parse_qs(parsed.query)
                        filters = {key: values[0] for key, values in params.items() if values}
                        self._api({"items": model.capabilities(filters)})
                        return
                    if path.startswith("/api/capabilities/"):
                        repository_id = int(path.rsplit("/", 1)[1])
                        item = next((card for card in model.capabilities() if card.get("repository_id") == repository_id), None)
                        self._api(item or {"error": "capability not found"}, 200 if item else 404)
                        return
                    if path == "/api/activity":
                        params = parse_qs(parsed.query)
                        limit = min(100, max(1, int(params.get("limit", [30])[0])))
                        self._api({"items": model.activity(limit)})
                        return
                    if path == "/api/documents":
                        self._api({"items": model.documents()})
                        return
                    if path == "/api/document":
                        relative = parse_qs(parsed.query).get("path", [""])[0]
                        source = model.document_text(relative)
                        self._api({"path": relative, "html": render_markdown(source)})
                        return
                    self._send(404, b"Not Found", "text/plain; charset=utf-8")
                except (ValueError, FileNotFoundError, OSError, sqlite3.Error) as error:
                    self._api({"error": str(error)}, 400)
                except Exception:
                    self._api({"error": "dashboard request failed"}, 500)

        last_error: OSError | None = None
        for candidate_port in range(self.port or 0, (self.port or 0) + 20):
            try:
                self.httpd = _DashboardHTTPServer((self.host, candidate_port), Handler)
                break
            except OSError as error:
                last_error = error
        if self.httpd is None:
            raise OSError("no available localhost dashboard port") from last_error
        address = f"http://{self.host}:{self.httpd.server_address[1]}"
        self.thread = Thread(target=self.httpd.serve_forever, name="techchancellor-dashboard", daemon=True)
        self.thread.start()
        return self.httpd, address

    def stop(self) -> None:
        if self.httpd is not None:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd = None


def serve_dashboard(root: str | Path, host: str = "127.0.0.1", port: int = 0,
                    open_browser: bool = True, desktop: bool = True,
                    open_obsidian: bool = False) -> int:
    server = DashboardServer(root, host, port)
    _, url = server.start()
    if open_obsidian:
        open_in_obsidian(Path(root).resolve())
    app_process = None
    if open_browser:
        if desktop:
            app_process = open_desktop_window(url)
        else:
            webbrowser.open(url)
    print(json.dumps({"status": "DASHBOARD_RUNNING", "url": url, "binding": host}, ensure_ascii=False))
    try:
        while app_process is None or app_process.poll() is None:
            if server.thread:
                server.thread.join(1)
    except KeyboardInterrupt:
        return 0
    finally:
        server.stop()
    return 0
