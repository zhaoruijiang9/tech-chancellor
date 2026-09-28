# TechChancellor Capability Library Curation V0.9 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reclassify the 14 reviewed repositories into an evidence-backed human library that separates usable capabilities, adopted methods, active validation, owner decisions, watchlist items, non-adoptions, and failed validation.

**Architecture:** Keep SQLite and append-only history authoritative. Add a read-only semantic projection that combines current Chancellor decisions, activation evidence, queue state, user feedback, real-use evidence, and the existing human usage metadata. Reuse that projection in the dashboard and generated human toolbox without changing discovery or activation policy.

**Tech Stack:** Python 3, SQLite, vanilla HTML/CSS/JavaScript, unittest.

## Global Constraints

- Do not discover new repositories, add capabilities, rerun the backlog, or access `D:\money`.
- Preserve the accepted Control Center visual baseline; reorganize semantics without redesigning the artwork or layout language.
- Keep all prior records and feedback; use a centralized derived projection rather than rewriting history.
- Default library view is `USED` and `USABLE`; adopted methods, pending work, and watch/archive states are separate.
- `APPROVE_FOR_REVIEW` means the owner already authorized follow-up review and must not be shown as an unresolved decision.
- Local commit is allowed; push is not allowed; do not move or recreate the `v0.1.0` tag.

---

### Task 1: Human Library Projection

**Files:**
- Create: `src/pti/human_library.py`
- Test: `tests/test_human_library.py`

**Interfaces:**
- Consumes: capability cards, activation evidence, latest feedback, queue facts, and human usage metadata.
- Produces: `project_human_library_item(card, queue_records) -> dict` with `human_category`, `item_kind`, `classification_reason`, `human_action_required`, `processing_state`, and evidence summary fields.

- [ ] Write failing tests for used capability, adopted method, reference-only watchlist, explicit non-adoption, approved validation, unresolved owner decision, and failed validation.
- [ ] Run `D:\python\python.exe -m unittest tests.test_human_library -v` and confirm the module is missing.
- [ ] Implement the smallest evidence-driven projection and run the focused tests to green.

### Task 2: Dashboard and Toolbox Integration

**Files:**
- Modify: `src/pti/dashboard_read_model.py`
- Modify: `src/pti/human_toolbox.py`
- Modify: `tests/test_dashboard_read_model.py`
- Modify: `tests/test_human_toolbox.py`

**Interfaces:**
- Consumes: `project_human_library_item`.
- Produces: category-aware capability cards, summary counts, and generated human toolbox sections.

- [ ] Add failing tests for category counts, default capability collection, resolved approval state, and method separation.
- [ ] Run focused tests and verify expected failures.
- [ ] Integrate the projection, retain raw machine fields for audit, and run focused tests to green.

### Task 3: Four-Section Human UI

**Files:**
- Modify: `src/pti/dashboard_assets/app.js`
- Modify: `src/pti/dashboard_assets/app.css`
- Modify: `src/pti/dashboard_assets/index.html`
- Modify: `tests/test_dashboard_assets.py`

**Interfaces:**
- Consumes: `human_category`, `item_kind`, `classification_reason`, `human_action_required`, and category counts.
- Produces: `我的能力`, `方法库`, `待处理`, and `观察与归档` views with `我的能力` as default.

- [ ] Add failing source-contract tests for the four sections, human status labels, owner-decision controls, and semantic home counts.
- [ ] Run the asset tests and confirm the new contracts fail.
- [ ] Update the existing UI in place without changing the accepted visual assets; run asset and server tests to green.

### Task 4: Full Inventory Report and Verification

**Files:**
- Create: `TECHCHANCELLOR_LIBRARY_CURATION_V0_9_REPORT.md`
- Modify only if needed: `TECHCHANCELLOR_HUMAN_CONTROL_CENTER_V0_8_REPORT.md`

**Interfaces:**
- Consumes: the live 14-item projection and retained database evidence.
- Produces: complete inventory table, category counts, Archon audit, unresolved owner decisions, and verification results.

- [ ] Generate the report from verified live evidence and confirm all 14 current records appear once.
- [ ] Run the full test suite, Python compile check, JavaScript syntax check, dashboard smoke, and `git diff --check`.
- [ ] Open the real local dashboard and click through all four library sections plus representative detail pages.
- [ ] Precisely stage the intended files, create one local logical commit, and verify the commit without pushing.
