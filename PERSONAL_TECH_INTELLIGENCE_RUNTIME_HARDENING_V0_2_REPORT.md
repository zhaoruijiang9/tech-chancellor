# PERSONAL_TECH_INTELLIGENCE_RUNTIME_HARDENING_V0_2_REPORT

Date: 2026-08-30
Scope: `D:\personal-tech-intelligence` only. `D:\money` was not read or modified.

## Final status

`PASS_UNATTENDED_RADAR_RUNTIME_V0_2`

The current unattended runtime path is accepted. The health command may report
`DEGRADED_HISTORY_ONLY` because pre-hardening duplicate decision history is
preserved as regression evidence; this is not a current runtime failure.

## Changes completed

- Stage A remains Tuesday/Friday at 20:30 and records a unique `scan_run_id`.
- A successful Stage A run triggers the formal Chancellor task only when active
  pending packets exist. The 30-minute Chancellor polling task was replaced by
  daily 03:30 recovery.
- Pending packets now use `repository--scan_run_id.json` identity.
- Packet lifecycle is `pending -> processing -> processed`; stale processing
  packets recover to retryable pending. Processed and raw files are never active.
- Completion is idempotent when a processed marker already exists.
- Lock files contain owner metadata and distinguish a live owner from stale,
  malformed, or unknown ownership. Stale legacy locks recover safely.
- Interrupted scan and Chancellor runs are persisted as interrupted/recovered,
  never silently reported as success.
- `stage_b_runs`, scan observations, decision history, and notification events
  provide structured execution evidence. Existing decision history was retained.
- `python run.py health` provides a read-only runtime health snapshot.

## Acceptance evidence

- Automated regression suite: 36 tests passed; compile check passed.
- Formal Stage A run at 01:49:33: Scheduler `Last Result=0`; scan status
  `SCAN_SUCCESS`; 20 candidates, 4 requests, 0 failures.
- Automatic Stage B run at 01:49:51: Scheduler `Last Result=0`; 3 packets claimed,
  3 standalone Codex invocations, 3 processed, 0 failures, 0 active pending.
- Standalone Codex network smoke returned exactly `{"status":"NETWORK_OK"}`.
- Daily recovery task is `Ready`, scheduled for 03:30, and its no-pending path
  previously completed with `Last Result=0` and zero Codex invocations.
- Final health snapshot: no active packets, no lock files, latest scan and Stage B
  runs completed successfully, and both formal tasks last returned 0.

## Known historical evidence

The database retains pre-hardening repeated decision history and old processed
filename chains. They are excluded from active packet discovery and were not
deleted, so regression evidence remains available for later comparison.

## Operational boundary

The Chancellor may inspect packet text only through standalone Codex in read-only
ephemeral mode. Candidate repositories are not executed, installed, imported,
served, or exposed as MCP. No broker, account, order, or `D:\money` access is
part of this system.
