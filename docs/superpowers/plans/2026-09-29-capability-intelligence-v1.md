# TechChancellor Capability Intelligence V1 Implementation Plan

**Goal:** Deliver an additive capability/method evidence model, truthful human projection, and low-frequency upstream delta detection without changing the accepted visual design or existing history.

**Architecture:** Add normalized SQLite tables behind a focused `capability_intelligence` service. Seed/migrate the 14 reviewed repositories deterministically, expose read projections to the existing dashboard, and attach a bounded monitor to the existing Radar launcher.

**Constraints:** TDD for each behavior; no `D:\money`; no auto-install or upgrade; precise staging; local commits only; no push; do not move `v0.1.0`.

## Task 1: Schema and Migration

- Add failing model tests for repository/capability separation, many-to-many mappings, method evidence, relations, personal states, fresh DB, and idempotent migration.
- Implement the additive schema and deterministic seed migration.
- Verify 14 reviewed sources survive one-to-one and legacy table counts do not change.

## Task 2: Truthful Human Semantics

- Add failing tests for method downgrade, adopted-method evidence gate, waiting versus active validation, and preserved owner decisions.
- Replace hard-coded adoption claims with evidence-backed projections.
- Add capability-centered library projections while retaining source-project views.

## Task 3: Continuous Intelligence

- Add failing tests for baseline capture, no-change reuse, meaningful change, idempotent delta queue, network/rate-limit/system failures, failed-source reopening, and no upgrade side effects.
- Implement bounded fingerprints and freshness persistence.
- Add the CLI action and nonblocking twice-weekly scheduler integration.

## Task 4: Dashboard and Observability

- Add failing read-model, HTTP, asset-contract, and health tests.
- Expose capability, method, source, implementation, freshness, and stale-review projections.
- Update copy and interactions only; preserve layout and visual assets.

## Task 5: Live Migration and Verification

- Back up the formal SQLite database and run the idempotent migration.
- Capture all 14 baselines, rerun to prove no-change, and use a temporary provider to prove change-to-delta-review without modifying any third-party project.
- Run the full suite, compile, JavaScript syntax, dashboard HTTP/UI smoke, and Git checks.
- Write `TECHCHANCELLOR_CAPABILITY_INTELLIGENCE_V1_REPORT.md`, create logical local commits, verify history, and do not push.
