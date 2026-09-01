# Current Project State

Snapshot date: 2026-09-02

## Scope

This repository is the independent `PERSONAL_TECH_INTELLIGENCE_SYSTEM` at
`D:\personal-tech-intelligence`. It must not read, scan, modify, or treat
`D:\money` as a data source.

## Source baseline

This snapshot establishes the first source-only Git baseline. Runtime state is
intentionally excluded from Git: SQLite, logs, pending and processed packets,
generated reports, generated library projections, credentials, and virtual
environment files.

## Runtime snapshot

- Stage A: Tuesday/Friday 20:30.
- Stage B: Stage A post-success trigger plus daily 03:30 recovery.
- Formal tasks: `PTI-Radar-Scan` and `PTI-Chancellor` only.
- Formal tasks run hidden PowerShell launchers with no-window Python/Codex child processes.
- Current pending count: 0 at the time of this baseline.
- Latest scan: `SCAN_NOT_EVALUATED` because two GitHub requests failed with
  SSL/remote connection errors; this is preserved as source coverage evidence.
- Latest Chancellor recovery: three pending packets processed successfully.

## Verification snapshot

- Existing test suite before MVP v1.2 work: 36 tests passed.
- Existing compile check: passed.
- Runtime health before MVP v1.2 work: `NOT_EVALUATED` only because the latest
  scan had source failures; no stale lock or active pending remained.

## Product boundary

Global Codex Skill installation is not part of this baseline. The planned next
gate is `GLOBAL_CODEX_SKILL_APPROVAL`. Candidate repository code is never
executed, installed, imported, served, or started as MCP.
