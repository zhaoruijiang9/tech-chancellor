# TechChancellor Control Center V0.8.3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the existing control center as a polished desktop product and provide a verified one-click Windows desktop entry.

**Architecture:** Keep the existing Python localhost server, SQLite read model, vanilla HTML/CSS/JS, and five-view information architecture. Add a portable Windows shortcut installer, make the browser app process own the server lifetime, and reshape the UI around a compact overview plus dedicated capability detail view.

**Tech Stack:** Python standard library, PowerShell/WScript.Shell, Windows `.cmd`, HTML, CSS, vanilla JavaScript, Edge app mode.

## Global Constraints

- Bind only to `127.0.0.1`; keep the dashboard read-only and preserve Markdown path restrictions.
- Keep the existing SQLite model and lifecycle semantics unchanged.
- Do not access or modify `D:\money`.
- Do not add frontend frameworks, network assets, installers, or release tags.
- Preserve Chinese-first UI and keep raw machine labels inside deliberate technical details only.
- Create the desktop shortcut only through an explicit command; never during clone, init, or normal dashboard startup.
- `AUTO_PUSH = NO`.

---

### Task 1: Canonical Windows launcher and desktop shortcut

**Files:**
- Modify: `tests/test_dashboard_cli.py`
- Create: `tests/test_windows_shortcut.py`
- Create: `src/pti/windows_shortcut.py`
- Create: `scripts/install_shortcut.ps1`
- Create: `打开技术丞相.cmd`
- Modify: `run.py`

**Interfaces:**
- Produces: `install_desktop_shortcut(root: Path) -> dict[str, str]`
- Produces: `python run.py install-shortcut`

- [ ] Write tests for relative launcher paths, UTF-8 mode, hidden `pythonw` preference, dynamic Desktop resolution, and the explicit CLI action.
- [ ] Run the focused tests and verify they fail because the launcher and installer do not exist.
- [ ] Implement the portable launcher, PowerShell shortcut installer, and CLI action.
- [ ] Run the focused tests and verify they pass.
- [ ] Create the current user's shortcut and verify its resolved target, working directory, and description.

### Task 2: Desktop shell lifecycle

**Files:**
- Modify: `tests/test_dashboard_server.py`
- Modify: `src/pti/dashboard_server.py`

**Interfaces:**
- Produces: `open_desktop_window(url: str, profile_root: Path | None = None) -> subprocess.Popen | None`
- `serve_dashboard(...)` stops its server after the dedicated app window exits.

- [ ] Write a failing test that requires dedicated Edge app arguments and browser-process lifetime tracking.
- [ ] Run the focused test and verify the current implementation fails.
- [ ] Implement the dedicated local browser profile and server shutdown behavior.
- [ ] Run dashboard server and focused tests until green.

### Task 3: Freeform visual completion

**Files:**
- Modify: `src/pti/dashboard_assets/index.html`
- Modify: `src/pti/dashboard_assets/app.js`
- Modify: `src/pti/dashboard_assets/app.css`

**Interfaces:**
- Keeps: `/api/summary`, `/api/capabilities`, `/api/activity`, `/api/documents`, `/api/document`.
- Adds client-only dedicated capability detail rendering from already-loaded read-model data.

- [ ] Recompose the desktop shell, overview, capability library, detail page, activity, system, and document reader using current database content.
- [ ] Run the dashboard and capture the first visual pass at desktop widths in light and dark themes.
- [ ] Critique density, hierarchy, long-title handling, empty states, and contrast from screenshots.
- [ ] Apply a second visual pass and recapture all six views.

### Task 4: Verification and delivery

**Files:**
- Modify: `TECHCHANCELLOR_HUMAN_CONTROL_CENTER_V0_8_REPORT.md`

- [ ] Run the full unit suite, compile checks, JavaScript syntax check, and `git diff --check`.
- [ ] Launch through `技术丞相.lnk`, verify the independent app window and live backend, then close it and verify no launched backend remains.
- [ ] Record V0.8.3 visual iterations, desktop shell, shortcut path, smoke result, test count, local head, ahead count, and `PUSH = NO`.
- [ ] Commit only the scoped project changes locally without pushing or moving tags.
