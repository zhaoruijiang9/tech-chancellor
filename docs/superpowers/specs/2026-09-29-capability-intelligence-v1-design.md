# TechChancellor Capability Intelligence V1 Design

## Goal

Separate reviewed sources from the capabilities and methods they may provide, then keep the review current with bounded upstream change detection. SQLite remains authoritative and existing repository, decision, feedback, activation, and history records remain untouched.

## Object Model

- `capability_sources`: where evidence comes from. The 14 reviewed GitHub repositories migrate here one-for-one.
- `capability_implementations`: a concrete tool, package, workflow, or integration supplied by a source.
- `capabilities`: a user-facing ability such as project architecture visualization.
- `implementation_capabilities`: many-to-many mapping with an explainable capability delta.
- `methods`: a concrete method or pattern, independent of its source repository.
- `method_evidence`: the mechanism and observed usage needed to justify adoption.
- `capability_relations`: evidence-backed capability-level relationships only.
- `personal_states`: state attached to a capability, implementation, or method rather than a repository.
- `source_freshness`: current and last-reviewed upstream fingerprints in separate columns.
- `upstream_check_runs` and `delta_review_queue`: observable, idempotent monitoring and review work.

The accepted repository history remains the source of legacy decisions. Capability Intelligence V1 is an additive migration and projection, not a rewrite.

## Evidence Rules

A method is `ADOPTED` only when it has both:

1. a concrete workflow mechanism, such as a Codex skill, policy, project constitution, or callable workflow; and
2. verified use evidence tied to that mechanism.

Distilled notes, README summaries, and a classification label are reference evidence only. On current evidence, BMAD and Spec Kit are method sources with `KNOWLEDGE_REFERENCE` methods, not adopted methods.

Personal states are explicit facts such as `VERIFIED`, `USED`, `AVAILABLE`, `REJECTED`, `DEPRECATED`, or workflow states such as `APPROVED_WAITING_VALIDATION`. An active validation requires an actual processing queue record; owner approval alone is not active work.

## Migration

Initialization creates the new schema idempotently. A deterministic migration maps every current semantic decision to one source and one implementation, then maps implementations to normalized capabilities. It preserves all old rows and may be run repeatedly without duplicates.

The migration creates six reference-only method records for BMAD and Spec Kit. Their evidence records explicitly state that no qualifying local mechanism or use evidence was found. Archify maps to `PROJECT_ARCHITECTURE_VISUALIZATION` with verified and used personal states. Backtesting Engine maps to `APPROVED_WAITING_VALIDATION`; TradingAgents remains `HUMAN_DECISION`; Archon remains validation-failed but reopenable when relevant blocker evidence changes.

## Continuous Intelligence

The monitor runs with the existing Radar schedule, Tuesday and Friday at 20:30. It is a separate subprocess whose result cannot change Radar's exit status.

Stage 1 uses bounded GitHub API metadata:

- repository `updated_at` and `pushed_at`;
- default-branch head SHA;
- latest release tag and publication time;
- README blob SHA for BMAD, Spec Kit, and Archon.

The first run records `BASELINE_CAPTURED`. Later runs first fetch repository metadata; unchanged metadata reuses the deeper fingerprint, keeping the no-change pass inexpensive. Network, rate-limit, and system failures are recorded separately.

Stage 2 creates one active delta-review item per changed source only when a release, reviewed document, or blocker-relevant change may affect the old judgment. Head-only changes with no relevant signal do not create a full review. No monitoring path installs, upgrades, pulls, or executes third-party code.

## Dashboard Projection

The accepted visual baseline is unchanged. The data model and copy change minimally:

- `我的能力` shows capability entities and their current implementation;
- `方法库` shows only adopted methods;
- `待处理` distinguishes waiting validation, active validation, and owner decisions;
- `观察与归档` shows source projects and method sources without calling them capabilities;
- details show entity type, implementation, source, current/reviewed upstream version, last check, and review freshness;
- the home page shows a compact stale-review entry only when needed.

## Safety

- No access to `D:\money`.
- No automatic install, update, pull, package operation, or activation.
- No destructive migration.
- A formal database backup precedes the live migration.
- Empty databases remain valid and can receive their first source-to-capability mapping.
