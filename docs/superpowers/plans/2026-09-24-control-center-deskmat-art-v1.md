# Control Center Deskmat Art V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current home artwork with an original deskmat-inspired panoramic intelligence-studio composition and integrate it as the visual foundation of the control center.

**Architecture:** Keep the existing local HTML/CSS/JavaScript dashboard and Python loopback server. Add two versioned raster assets, update the asset allowlist, and reshape only the presentation layer; existing APIs and navigation behavior remain intact.

**Tech Stack:** Python `unittest`, static HTML, CSS, vanilla JavaScript, local PNG assets, built-in image generation.

## Global Constraints

- Keep all changes inside `D:\personal-tech-intelligence`.
- Do not modify or integrate with `D:\money`.
- Do not add remote image, font, or JavaScript dependencies.
- Use one dominant panoramic illustration and one secondary five-panel atlas.
- Preserve keyboard focus, reduced motion, desktop, and mobile support.
- Do not commit automatically; the user controls publication and commit timing.

---

### Task 1: Lock the local art contract

**Files:**
- Modify: `tests/test_dashboard_assets.py`
- Modify: `tests/test_dashboard_server.py`

**Interfaces:**
- Consumes: the current static dashboard asset contract.
- Produces: failing assertions for `advisor-studio-v2.png` and `capability-studio-v2.png`.

- [x] Add assertions that CSS references both versioned local assets and contains the panoramic stage hooks.
- [x] Add HTTP assertions that the server serves both PNG assets with `image/png`.
- [x] Run the two test modules and confirm they fail because the new asset contract is absent.

### Task 2: Generate and register the original artwork

**Files:**
- Create: `src/pti/dashboard_assets/advisor-studio-v2.png`
- Create: `src/pti/dashboard_assets/capability-studio-v2.png`
- Modify: `src/pti/dashboard_server.py`

**Interfaces:**
- Consumes: the approved reference synthesis in the design spec.
- Produces: two self-contained local PNG assets available at `/assets/<filename>`.

- [x] Generate the panoramic adviser studio with quiet left-side negative space and an adult adviser on the right.
- [x] Generate the five-panel atlas in the same palette and medium.
- [x] Inspect both images for subject, composition, unwanted text, logos, and clutter.
- [x] Add both names to the server asset allowlist.
- [x] Run server asset tests and confirm they pass.

### Task 3: Recompose the home screen around the artwork

**Files:**
- Modify: `src/pti/dashboard_assets/app.css`
- Modify: `src/pti/dashboard_assets/app.js`
- Modify: `src/pti/dashboard_assets/index.html`

**Interfaces:**
- Consumes: the two local PNG paths and existing summary/capability APIs.
- Produces: one panoramic home stage, one featured intelligence block, and one secondary five-panel capability strip.

- [x] Replace the current home artwork references and add the new stage selectors.
- [x] Reduce the featured panel opacity, border weight, and visual footprint.
- [x] Integrate navigation into the scene edge while preserving all five destinations.
- [x] Rework desktop and mobile crops so the subject remains visible and text stays readable.
- [x] Run JavaScript syntax and dashboard asset tests.

### Task 4: Visual and regression verification

**Files:**
- Verify: `src/pti/dashboard_assets/*`
- Verify: `tests/*`

**Interfaces:**
- Consumes: the completed static frontend and loopback server.
- Produces: verified desktop/mobile screenshots and a green regression suite.

- [x] Start the loopback dashboard and inspect the home screen at desktop width.
- [x] Inspect a narrow mobile viewport and dark theme.
- [x] Remove any element that competes with the adviser or fragments the composition.
- [x] Run `python -m unittest discover -s tests -p 'test_*.py'`, `python -m compileall -q src run.py`, `node --check src/pti/dashboard_assets/app.js`, and `git diff --check`.
