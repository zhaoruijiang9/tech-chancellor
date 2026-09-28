# TechChancellor Capability Library Curation V0.9

## Scope

This pass audited the 14 records already present in the PTI SQLite state and rebuilt only the human-facing library projection. It did not discover new repositories, install new software, rerun the activation backlog, or access `D:\money`.

Evidence sources were the current repository records, Chancellor decisions, activation records, activation queue history, human feedback, real-use evidence, generated reference notes, and the existing local capability usage profile. SQLite remains authoritative; the dashboard and `MY_CAPABILITIES.md` are derived views.

## Corrected Inventory

`14` is the number of reviewed projects, not the number of installed capabilities.

| Human category | Count | Meaning |
| --- | ---: | --- |
| USED | 1 | Installed, callable, and supported by real-use evidence |
| USABLE | 0 | Validated and callable, but without real-use evidence |
| ADOPTED_METHOD | 2 | Distilled methods used in the current workflow, not installed tools |
| VALIDATING | 1 | User approval already exists; the system may continue bounded review |
| HUMAN_DECISION | 1 | A real owner decision is still required |
| WATCHLIST | 6 | Retained as projects or references for future comparison |
| NOT_ADOPTED | 2 | Reviewed but not adopted because current capability overlap is high |
| VALIDATION_FAILED | 1 | Controlled activation review stopped safely before installation |
| ARCHIVED | 0 | No current record meets the archive rule |

Dashboard summary:

- Available capabilities: 1
- Adopted methods: 2
- Processing: 1
- Watchlist: 6
- Reviewed projects: 14

## Full 14-Record Audit

| Project | Raw semantic / activation state | Human type | Human category | Installed / runnable | Why retained | Next step |
| --- | --- | --- | --- | --- | --- | --- |
| `tt-a1i/archify` | `CANDIDATE_FOR_QUARANTINE / USED` | CAPABILITY | USED | Yes / Yes | Pinned, statically reviewed, isolated test passed, controlled trial enabled, and used successfully on an authorized real task | Continue bounded use and retain rollback/security boundaries |
| `github/spec-kit` | `REFERENCE_ONLY / ACTIVE_PATTERN` | PATTERN_METHOD | ADOPTED_METHOD | No / No | Its specification-first and acceptance-gate patterns were distilled into the current workflow | Use selectively on boundary-heavy work; do not install the full toolchain |
| `bmad-code-org/BMAD-METHOD` | `REFERENCE_ONLY / ACTIVE_PATTERN` | PATTERN_METHOD | ADOPTED_METHOD | No / No | Its clarify-plan-implement-verify pattern was distilled and is used as a method | Use the distilled pattern only; do not install the full runtime |
| `nieledran/backtesting-engine` | `CANDIDATE_FOR_QUARANTINE / BLOCKED_HUMAN` | CANDIDATE | VALIDATING | No / No | The owner already selected `APPROVE_FOR_REVIEW`; this is system work, not another owner decision | Continue only in public/synthetic-data isolation; no broker, account, or `D:\money` access |
| `TauricResearch/TradingAgents` | `REFERENCE_ONLY / BLOCKED_HUMAN` | CANDIDATE | HUMAN_DECISION | No / No | Financial multi-agent direction may be relevant, but code, data sources, safety boundaries, and outcomes remain unverified | Owner may choose isolated review, watch, or not adopt; any review must use public/synthetic data only |
| `coleam00/archon` | `CANDIDATE_FOR_QUARANTINE / FAILED_WITH_EXPLAINED_REASON` | CANDIDATE | VALIDATION_FAILED | No / No | The workflow concept remains useful evidence, but safe reproducible activation was not available | Reconsider only with a pinned version, rollback path, isolated execution route, and a concrete unmet need |
| `langchain-ai/langchain` | `REFERENCE_ONLY / ACTIVE_PATTERN` | PROJECT | NOT_ADOPTED | No / No | Reviewed reference with high overlap against the current stack and no validated capability delta | Recompare only when a concrete integration gap appears |
| `FoundationAgents/MetaGPT` | `REFERENCE_ONLY / ACTIVE_PATTERN` | PROJECT | NOT_ADOPTED | No / No | Architecture reference with high overlap, heavy integration cost, and no proven delta | Do not install; revisit only for a specific unmet orchestration need |
| `volcengine/MineContext` | `WATCH / ACTIVE_PATTERN` | PROJECT | WATCHLIST | No / No | Desktop context collection is directionally relevant but carries privacy and operating-boundary costs | Observe only; do not enable background collection |
| `headroomlabs-ai/headroom` | `WATCH / ACTIVE_PATTERN` | PROJECT | WATCHLIST | No / No | Context compression may become useful if context cost becomes a measured bottleneck | Observe until the bottleneck is demonstrated |
| `gmickel/flow-next` | `REFERENCE_ONLY / ACTIVE_PATTERN` | KNOWLEDGE_REFERENCE | WATCHLIST | No / No | Useful comparison material for orchestration and fresh-context worker patterns | Keep as design reference, not a replacement runtime |
| `ComposioHQ/awesome-claude-skills` | `REFERENCE_ONLY / ACTIVE_PATTERN` | KNOWLEDGE_REFERENCE | WATCHLIST | No / No | Discovery index only; inclusion does not imply safety or installability | Use only for manual discovery and independently review every candidate |
| `chunkhound/chunkhound` | `REFERENCE_ONLY / ACTIVE_PATTERN` | PROJECT | WATCHLIST | No / No | Codebase semantic retrieval is relevant, but no local capability delta has been validated | Observe; do not install a service or MCP yet |
| `cased/kit` | `REFERENCE_ONLY / ACTIVE_PATTERN` | KNOWLEDGE_REFERENCE | WATCHLIST | No / No | Useful reference for repository context and symbol organization | Recompare if repository retrieval becomes a measured bottleneck |

## Archon Finding

- Installed: NO
- Runnable now: NO
- Isolated test: NOT RUN
- Activation queue: `FAILED_TERMINAL`
- Attempt count: 1
- Failure: `SAFE_REPRODUCIBLE_ACTIVATION_NOT_AVAILABLE`
- Missing evidence: pinned version, rollback path, isolated execution evidence, and a proven capability delta

The failure is a safe validation stop, not a broken installation. No unsafe execution was attempted. Archon remains visible under “观察与归档” because its workflow ideas are still useful reference material, but it is not represented as an installed capability.

## Owner Decisions

`TauricResearch/TradingAgents` is the only unresolved owner decision.

`nieledran/backtesting-engine` is not an unresolved decision. The latest persisted owner feedback is `APPROVE_FOR_REVIEW`; the dashboard therefore shows “正在处理” and does not ask the same question again.

## Human Interface

The capability library now opens on “我的能力” and separates four views:

1. 我的能力: USED + USABLE
2. 方法库: ADOPTED_METHOD
3. 待处理: VALIDATING + HUMAN_DECISION
4. 观察与归档: WATCHLIST + NOT_ADOPTED + VALIDATION_FAILED + ARCHIVED

Each detail page exposes why the item remains in the library, its next step, item type, installation state, and current runnability. Decision buttons appear only when `human_action_required` is true.

## Verification

- Full test suite: 109 PASS
- Python compile check: PASS
- JavaScript syntax check: PASS
- Dashboard HTTP/API smoke: PASS
- Real Microsoft Edge UI: PASS across all four library sections and the Archify, backtesting-engine, TradingAgents, and Archon detail states
- Browser console: no product errors; one unrelated browser-extension warning was observed
- Git diff check: PASS
- Accepted visual baseline: preserved
- `D:\money`: not accessed
- Push: NO

## Final Status

LIBRARY_CURATION = PASS

REVIEWED_PROJECTS = 14

REAL_CAPABILITIES = 1

ADOPTED_METHODS = 2

UNRESOLVED_OWNER_DECISIONS = 1

PUBLICATION = LOCAL_COMMIT_ONLY
