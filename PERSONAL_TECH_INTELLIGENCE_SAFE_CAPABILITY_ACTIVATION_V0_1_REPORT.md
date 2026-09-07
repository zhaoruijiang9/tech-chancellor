# PTI Discovery Fairness and Safe Capability Activation v0.1

## Discovery fairness

- `QUERY_TEMPLATES`: 8 configured queries across AI_AGENT, AI_EXPERIENCE, QUANT_DATA, and PRODUCTIVITY.
- `QUERY_FIRST_PASS_COVERAGE`: 100% in the formal live Radar run (`run_id=69573283220d`).
- `REQUESTS_USED`: 8 search requests.
- `RAW_CANDIDATES`: 40 source-query observations in the formal run.
- `UNIQUE_CANDIDATES`: 40 stable GitHub IDs observed before the final cap.
- `FINAL_CANDIDATES`: 20, bounded by `total_candidate_cap=20`.
- `QUERY_STARVATION`: PASS; all eight queries executed before the final cap was applied.
- Cross-query matches retain one observation per source query; final candidate identity counts once.

## Activation policy

| Tier | Boundary | Automatic action |
|---|---|---|
| TIER_0_KNOWLEDGE_PATTERN | Read, compare, and reference | Allowed |
| TIER_1_DECLARATIVE_SKILL | Quarantine, static analysis, isolated smoke/test | Allowed only after safety gates |
| TIER_2_LOW_PRIVILEGE_LOCAL_TOOL | Quarantine, static analysis, isolated install/test | Global deployment remains off by default |
| TIER_3_SERVICE_OR_HIGH_INTEGRATION | Static analysis only | Human approval before execution |
| TIER_4_SENSITIVE_TRADING_OR_PRIVILEGED | Trading, broker, credential, admin, or privileged scope | Human approval always |

`AUTO_ACTION_BOUNDARY`: read/reference and low-risk quarantine/static/isolated validation. No persistent service, credential access, admin change, browser extension, system network/security change, broker action, or `D:\money` access.

Activation state and evidence maturity are stored in SQLite `activation_records`. Existing cards remain `REVIEWED` unless a bounded test has actually passed.

## Archify controlled pilot

- `REPOSITORY`: `tt-a1i/archify` (GitHub repository id `1211139949`)
- `PINNED_COMMIT`: `c6519401f7b91b9d43011657880893b0a8955548`
- `ACTIVATION_TIER`: `TIER_2_LOW_PRIVILEGE_LOCAL_TOOL`
- `STATIC_ANALYSIS`: PASS for the reviewed pinned source and package manifest. MIT license. The source contains Node child-process orchestration, file writes/renames, optional loopback preview, optional browser visual-check, and an update-check path. npm dependencies were installed only in the PTI quarantine with `--ignore-scripts`; no global install or candidate install script ran.
- `ISOLATED_TEST`: PASS. A PTI-only five-component fixture rendered and delivered in a quarantine output directory.
- `OUTPUT_QUALITY`: PASS, 9/9 showcase checks, 0 composition errors, 0 warnings; delivery receipt emitted SHA-256 and byte counts.
- `CAPABILITY_DELTA_AFTER_TEST`: deterministic architecture HTML/SVG with geometry validation, stable receipts, and failure diagnostics. The Codex baseline is a factual Markdown summary without those artifact checks or receipts.
- `EVIDENCE_MATURITY`: `TESTED`.
- `ACTIVATION_DECISION`: `TESTED_NOT_ADOPTED`.
- `TRIAL_STATUS`: `NOT_ENABLED` globally; source remains quarantined.
- `ROLLBACK_STATUS`: `READY`; no global state was changed, so rollback is quarantine removal only.

## Existing capability cards

The generated cards under `library/generated/repositories` now expose tier, activation state, evidence maturity, test status, and rollback status. Knowledge/pattern cards are read-only eligible; local tools remain quarantine-ready; TradingAgents is TIER_4 and cannot be auto-activated.

## Pattern extraction

`library/generated/references/BMAD-SPEC-KIT-PATTERN_DELTA.md` records the useful BMAD/Spec Kit ideas: compact decision packets, specification before implementation, explicit gates, and traceable artifacts. These are reference-only and do not alter the current runtime.

## Final status

```text
TASK_STATUS = PASS_WITH_CONTROLLED_PILOT
RUNTIME_STATUS = VERIFIED
DISCOVERY_STATUS = PASS_FAIR_FIRST_PASS
ACTIVATION_POLICY_STATUS = PASS_SQLITE_AUTHORITATIVE
ARCHIFY_STATUS = TESTED_NOT_ADOPTED
CAPABILITY_LIBRARY_STATUS = PASS_14_CARDS_REBUILT
GLOBAL_PTI_SKILL_STATUS = UNCHANGED
PRODUCT_VALUE_STATUS = IMPROVED_DISCOVERY_COVERAGE_AND_VALIDATED_DIAGRAM_CAPABILITY
FIRST_REAL_BLOCKER = GLOBAL_ARCHIFY_DEPLOYMENT_REQUIRES_SEPARATE_TIER_2_APPROVAL
NEXT_MODE = HUMAN_REVIEW_OR_KEEP_QUARANTINED
```
