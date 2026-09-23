# TechChancellor Human Control Center v0.8 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local, read-only TechChancellor Control Center that makes the existing SQLite-backed capability state, activity, health, and Markdown reports understandable from one Windows entry point.

**Architecture:** SQLite and the existing PTI backend remain authoritative. A Python standard-library read model aggregates existing tables and generated Human Toolbox metadata; a localhost HTTP server exposes JSON read endpoints and safe Markdown rendering; a small HTML/CSS/JS client is shared by the default desktop launcher and ordinary browser fallback. The default desktop mode uses the installed Obsidian reader only for document handoff, never as a dashboard runtime dependency.

**Tech Stack:** Python 3.11+ standard library (`sqlite3`, `http.server`, `webbrowser`, `subprocess`), HTML/CSS/vanilla JavaScript, Markdown rendered through a safe allowlisted renderer, Windows `.cmd` launchers, `unittest`.

## Global Constraints

- Bind only to `127.0.0.1`; never `0.0.0.0`.
- SQLite remains the sole authoritative state; do not add an event database or UI state database.
- Dashboard actions are read-only except regenerating the existing Human Toolbox export.
- Do not trigger discovery, Chancellor review, activation, deletion, policy changes, or protected-project access.
- Do not access or modify `D:\money`; do not hardcode user paths, personal capability data, or current SQLite contents.
- Keep the public project dependency-free beyond Python standard library and existing optional tools.
- Use `--no-browser` for testability; use a dynamic available port when the requested port is occupied.
- Markdown routes may read only approved project documentation roots and must reject traversal.
- Keep `v0.1.0` unchanged; this is a post-release local development change and does not create or push a tag.

---

### Task 1: Read Model and Safe Markdown Index

**Files:**
- Create: `src/pti/dashboard_read_model.py`
- Test: `tests/test_dashboard_read_model.py`

**Interfaces:**
- `DashboardReadModel(root: str | Path, db_path: str | Path | None = None)`
- `DashboardReadModel.snapshot() -> dict`
- `DashboardReadModel.capabilities(filters: dict | None = None) -> list[dict]`
- `DashboardReadModel.capability(repository_id: int) -> dict | None`
- `DashboardReadModel.activity(limit: int = 30) -> list[dict]`
- `DashboardReadModel.documents() -> list[dict]`
- `DashboardReadModel.document_text(relative_path: str) -> str`
- `DashboardReadModel.health() -> dict`

- [ ] **Step 1: Write failing tests** for empty database behavior, current capability counts, recent sorting, document categorization, and traversal rejection.
- [ ] **Step 2: Run `PYTHONUTF8=1 PYTHONPATH=src python -m unittest tests.test_dashboard_read_model -v` and observe failures.**
- [ ] **Step 3: Implement read-only SQL queries using existing `Database` schema and `health_report`; map machine states to Chinese human labels without changing stored state.**
- [ ] **Step 4: Build activity by merging scan runs, decision history, activation queue/records, and usage fields; sort newest first and preserve source/event type.**
- [ ] **Step 5: Index only root Markdown files plus `docs/`, `reports/`, and the final release/hardening reports; resolve paths under root and reject `..`, absolute paths, symlinks escaping root, and non-indexed files.**
- [ ] **Step 6: Run the focused tests and then the full suite; commit the read model.**

### Task 2: Local HTTP/API Server and Safe Markdown Rendering

**Files:**
- Create: `src/pti/dashboard_server.py`
- Test: `tests/test_dashboard_server.py`

**Interfaces:**
- `DashboardServer(root: str | Path, host: str = "127.0.0.1", port: int = 0)`
- `DashboardServer.start() -> tuple[ThreadingHTTPServer, str]`
- `DashboardServer.stop() -> None`
- `serve_dashboard(root: str | Path, host: str, port: int, open_browser: bool) -> int`

- [ ] **Step 1: Write failing tests** for loopback binding, `/api/summary`, `/api/capabilities`, `/api/activity`, `/api/documents`, `/api/document`, 404 handling, and unsafe Markdown escaping.
- [ ] **Step 2: Run the focused server tests and confirm they fail before implementation.**
- [ ] **Step 3: Implement `ThreadingHTTPServer` with an immutable root-bound handler, JSON responses, UTF-8 headers, no directory listing, and no credential/session endpoints.**
- [ ] **Step 4: Implement safe Markdown conversion for headings, paragraphs, lists, code blocks, links, and emphasis; escape raw HTML and allow only `http(s)`/relative approved document links.**
- [ ] **Step 5: Add dynamic port selection, clean shutdown, `webbrowser.open`, and `--no-browser` support without creating a service or orphan process.**
- [ ] **Step 6: Run focused and full tests; commit the server.**

### Task 3: Human Control Center UI

**Files:**
- Create: `src/pti/dashboard_assets/index.html`
- Create: `src/pti/dashboard_assets/app.css`
- Create: `src/pti/dashboard_assets/app.js`
- Test: `tests/test_dashboard_assets.py`

**Interfaces:**
- The client consumes only the JSON endpoints from Task 2.
- Navigation views: `home`, `capabilities`, `activity`, `system`, `documents`.

- [ ] **Step 1: Write asset tests** that confirm the required navigation labels, empty-state text, and endpoint references exist.
- [ ] **Step 2: Implement a Chinese-first desktop UI with five compact views: 首页, 能力库, 最近动态, 系统状态, 文档.**
- [ ] **Step 3: Render lifecycle labels for recently discovered, under review, validating, directly usable, used, knowledge/reference, not adopted, human decision, and failure/exception; place raw machine fields in a details disclosure.**
- [ ] **Step 4: Add capability search/status/category filters, recent-first sorting, detail view, copy-to-clipboard for `how_to_ask_codex`, and explicit empty states.**
- [ ] **Step 5: Add documents/report index and browser Markdown viewer; add links for README, CONTRIBUTING, reports, and local document opening without arbitrary file access.**
- [ ] **Step 6: Add restrained responsive CSS with no gradients, no heavy framework, no horizontal overflow, and clear warning/notice styling. Run asset tests and inspect the live page.**

### Task 4: CLI, Windows Entry, and Obsidian Handoff

**Files:**
- Modify: `run.py`
- Create: `打开技术丞相.cmd`
- Modify: `.gitignore`
- Test: `tests/test_dashboard_cli.py`

**Interfaces:**
- `python run.py dashboard [--host 127.0.0.1] [--port 0] [--no-browser]`
- `python run.py dashboard --open-obsidian` may hand off the project root to an installed Obsidian executable when detected; it must remain optional.

- [ ] **Step 1: Write failing CLI tests** for dashboard argument parsing, loopback defaults, `--no-browser`, and absence of privileged/system-service behavior.
- [ ] **Step 2: Implement the `dashboard` action and route static assets through `DashboardServer`; keep all other CLI actions unchanged.**
- [ ] **Step 3: Implement `打开技术丞相.cmd` using `%~dp0`, UTF-8 environment setup, a local `.venv` fallback, and `run.py dashboard`; do not embed an absolute path.**
- [ ] **Step 4: Add `.obsidian/` to local ignore rules and expose only a safe optional Obsidian handoff; never create vault metadata automatically.**
- [ ] **Step 5: Run CLI tests and a subprocess smoke with `--no-browser`; commit the entry path.**

### Task 5: End-to-End Verification and Report

**Files:**
- Create: `TECHCHANCELLOR_HUMAN_CONTROL_CENTER_V0_8_REPORT.md`
- Modify: `README.md`
- Modify: `README.zh-CN.md`

- [ ] **Step 1: Run the full unit suite, compile check, dashboard subprocess smoke, path-traversal test, and empty-database smoke.**
- [ ] **Step 2: Start the real dashboard on localhost and verify 首页、能力库、能力详情、最近动态、系统状态、文档 in a browser; confirm Chinese rendering and no horizontal overflow.**
- [ ] **Step 3: Verify Obsidian installation and open `README.zh-CN.md` without modifying it; record actual reader and smoke result.**
- [ ] **Step 4: Verify `打开技术丞相.cmd` launches the dashboard and the browser fallback remains available.**
- [ ] **Step 5: Write the concise report with actual counts, statuses, first real blocker, local commit, and `AUTO_PUSH=NO`; do not push.**
- [ ] **Step 6: Run `git diff --check`, confirm clean/intentional worktree state, and commit the completed v0.8 implementation locally.**
