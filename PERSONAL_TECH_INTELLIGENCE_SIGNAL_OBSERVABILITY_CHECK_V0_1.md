# PERSONAL_TECH_INTELLIGENCE_SIGNAL_OBSERVABILITY_CHECK_V0_1

**Date:** 2026-08-27  
**Status:** `OBSERVABILITY_SUFFICIENT_WITH_MINIMAL_PATCH`  
**Next mode:** `PASSIVE_SIGNAL_OBSERVATION`

## 1. What the Current Evidence Chain Already Preserves

Before this check, the system already preserved:

- Stable GitHub repository identity, canonical name, URL, current ledger state, scores, routes, and timestamps.
- Current deterministic candidate artifacts in `inbox` and the latest report.
- Pending Chancellor packets, raw Codex results, validated decision artifacts, processed packet names, and current SQLite Chancellor decisions.
- Partial enrichment content and source failures inside candidate/pending evidence.
- Feedback labels, notes, repository identity, and feedback timestamps.
- Scheduled scan and Chancellor runner logs, task commands, exit results, and PTI-only working paths.

This was enough to explain the current sample, but not enough to reliably compare multiple future observations of the same recommendation.

## 2. Gaps That Would Affect Future Calibration

The following gaps were real, not merely cosmetic:

- No durable scan/run identity joined a candidate observation to one scheduled cycle.
- Query text and source group were present in transient candidate evidence but not stored as append-only per-run observations.
- `repositories` stored only the current deterministic state; `chancellor_decisions` stored only one current decision per repository. Repeated high-duplication reviews, WATCH changes, and decision drift could not be reconstructed.
- Feedback could be tied to a repository, but not reliably to the recommendation run, route, report, or Chancellor decision that caused it.
- Notification policy existed, but no event record could distinguish not-required, sent, and failed outcomes. `USER_VISIBLE_SIGNAL_RATE` therefore could not be calculated.
- Historical enrichment degradation was visible in some packets but lacked a durable run-level observation join.

Without these links, future calibration could not reliably answer which query family generated a false positive, whether a project was repeatedly sent to semantic review, whether a route changed, or whether a user-visible recommendation was useful.

## 3. Nice-to-Have Gaps

These were intentionally not built:

- Immutable report snapshots or a full event-sourcing framework.
- Notification delivery provider integration.
- Dashboard, telemetry service, queue, vector database, or workflow engine.
- Automated statistical significance thresholds or automatic weight changes.
- Candidate-level code execution telemetry. Candidate code remains prohibited from execution.

They may improve convenience later, but they are not required for the next passive observation period.

## 4. Minimal Patch Applied

SQLite was extended in place and idempotently with:

- `scan_runs`: run identity, start/end time, status, request count, candidate count, and failure count.
- `candidate_observations`: append-only run, repository, source query/group, deterministic score/outcome, priority, enrichment level, degradation details, and observation time.
- `chancellor_decision_history`: append-only semantic decision history while retaining the existing unique current-decision table for idempotent state.
- `notification_events`: lightweight `NOTIFICATION_NOT_REQUIRED`, `NOTIFICATION_SENT`, or `NOTIFICATION_FAILED` records with reason, route, report, and run links.
- Optional feedback links: scan run, route, report path, and Chancellor history ID.

Existing `intelligence.db` data was preserved. The migration was run twice successfully; existing counts remained `repositories=20`, `chancellor_decisions=3`, and `user_feedback=0`. Historical rows before this patch cannot be retroactively assigned a run identity, which is recorded as an evidence limitation rather than fabricated.

The patch does not alter query selection, scoring, routing, scheduler definitions, notification policy, repository identity, quarantine, or static analysis behavior.

## 5. Verification

- Standard test suite: **27 passed**.
- Python compilation: **passed**.
- SQLite migration: **passed twice** on the existing database.
- Existing scheduled task commands still point only to `D:\personal-tech-intelligence`.
- No candidate dependency installation, candidate import, shell execution, MCP launch, server launch, or binary execution occurred.
- `D:\money` was not accessed or modified.

## 6. Calibration Gate

`REAL_EVIDENCE_BEFORE_CALIBRATION = REQUIRED`

Do not change scoring, routing, queries, blacklist rules, or notification thresholds until there are multiple independent scheduled scan cycles, semantic decisions outside `AI_AGENT`, real `AI_EXPERIENCE` semantic cases, repeated high-duplication observations, and actual user feedback.

The new tables make those future comparisons possible; they do not pretend the current sample is larger than it is.

## 7. Final Decision

`OBSERVABILITY_SUFFICIENT_WITH_MINIMAL_PATCH`

`PASSIVE_SIGNAL_OBSERVATION = YES`

The product should now run on its existing schedule and collect real signal quality evidence. No further infrastructure or calibration work is justified in this checkpoint.

`UNKNOWN_CODE_EXECUTION = NO`

`D:\money AUTO_MODIFICATION = NEVER`
