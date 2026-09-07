# PTI High-Relevance Discovery Blind-Spot Audit v0.1

Date: 2026-09-06
Project: `D:\personal-tech-intelligence`
Scope: discovery recall and capability-library expansion only. No candidate code was installed, imported, executed, or started. `D:\money` was not read or modified.

## Runtime

```text
RUNTIME_INCIDENT_STATUS = CURRENTLY_NOT_REPRODUCIBLE
CURRENT_RUNTIME_HEALTH = DEGRADED_HISTORY_ONLY
RUNTIME_ACTION = PASSIVE_OBSERVATION
```

The formal runtime smoke before this audit succeeded: Radar `SCAN_SUCCESS`, Scheduler `Last Result=0`, automatic Stage A -> Stage B, three pending processed, and three Codex invocations successful. The current degraded label is history-only (`LEGACY_DUPLICATE_HISTORY_PRESERVED`); no new runtime failure was introduced here.

## Identity Resolution

| User reference | Canonical public identity | Stable GitHub repository ID | Source type |
|---|---|---:|---|
| Archify | `tt-a1i/archify` | `1211139949` | repository |
| BMAD-METHOD | `bmad-code-org/BMAD-METHOD` | `965615190` | repository |
| Archon | `coleam00/archon` | `929121414` | repository |
| GitHub Spec Kit | `github/spec-kit` | `1042367133` | repository |
| Karpathy llm-wiki | `karpathy/442a6bf555914893e9891c11519de94f` | N/A | Gist |

Identity evidence came from the public GitHub repository pages, public README/docs, and the canonical Karpathy Gist. The local PTI ledger had no pre-existing rows or candidate observations for the four repository identities before this user-requested review.

## Candidate Review

All four repository candidates were submitted as `USER_REQUESTED` packets to the existing formal Chancellor. Four of four packets completed, four of four Codex reviews succeeded, and no pending packet remained.

| Repository | Semantic action | Route | Capability delta | Evidence maturity | Authorization |
|---|---|---|---|---|---|
| `tt-a1i/archify` | `CANDIDATE_FOR_QUARANTINE` | `AI_AGENT` | Specialized typed architecture/workflow maps, deterministic validation claims, and self-contained exports | `REVIEWED` | user approval required |
| `bmad-code-org/BMAD-METHOD` | `REFERENCE_ONLY` | `AI_AGENT` | Opinionated AI-agile method, role vocabulary, and workflow templates; no unique executable delta shown | `REVIEWED` | auto-read reference |
| `coleam00/archon` | `CANDIDATE_FOR_QUARANTINE` | `AI_AGENT` | Possible YAML-defined repeatable coding harness across planning, implementation, validation, and review | `REVIEWED` | user approval required |
| `github/spec-kit` | `REFERENCE_ONLY` | `AI_AGENT` | Packaged Spec -> Plan -> Tasks -> Implement workflow and integration ecosystem | `REVIEWED` | auto-read reference |

These are reviewed references, not tested or used capabilities. Popularity was not used as a value verdict.

## Karpathy Reference

```text
KARPATHY_LLM_WIKI_REFERENCE = EXTERNAL_DESIGN_REFERENCE
PTI_RELEVANCE = HIGH_FOR_KNOWLEDGE_COMPILATION_DESIGN
IMPLEMENT_NOW = NO
```

The Gist describes a three-layer pattern: immutable raw sources, an LLM-maintained interlinked Markdown wiki, and a schema describing ingestion/query/lint conventions. Its useful PTI implication is a future projection from repository evidence to reviewed capability concept to cross-repository synthesis. PTI already has an SQLite ledger, evidence packets, semantic decisions, capability cards, and contextual search; it still lacks durable contradiction/staleness lint and source-linked cross-capability synthesis. No graph database, ontology engine, embeddings, vector search, MCP, or external-source subsystem is justified now.

Reference file: `library/generated/references/karpathy-llm-wiki.md`.

## Discovery Blind Spot

Current pre-audit discovery configuration had five query templates, all generic and with the existing domain queries constrained by `language:python`. It did not contain vocabulary for coding-agent workflow, specification-driven development, architecture visualization, or agent harnesses.

| Candidate | MISS_CLASSIFICATION | Evidence |
|---|---|---|
| Archify | `QUERY_NOT_COVERED` with historical evidence limitation | Architecture visualization, diagram-as-code, and agent-skill vocabulary are absent from the pre-audit queries; no ledger or candidate observation existed to prove a historical result loss. |
| BMAD-METHOD | `QUERY_NOT_COVERED` with historical evidence limitation | AI-driven development method, role-based workflow, and coding-agent workflow vocabulary are absent; the generic Python agent query is not equivalent coverage. |
| Archon | `QUERY_NOT_COVERED` with historical evidence limitation | Coding-agent harness, repeatable workflow, and YAML orchestration vocabulary are absent; no identity or observation row existed before this audit. |
| GitHub Spec Kit | `QUERY_NOT_COVERED` with historical evidence limitation | Spec-driven development and specification workflow vocabulary are absent; Markdown/CLI workflow projects are also poorly represented by Python-only queries. |

No candidate was classified as `NOT_MISSED`, `DISCOVERED_BUT_PREFILTERED`, or `DISCOVERED_BUT_REVIEW_ALLOCATION_LOST`, because the local evidence does not contain historical raw search-result pages for those repositories. The audit deliberately preserves that uncertainty.

## Query Decision

```text
DISCOVERY_QUERY_PATCH = JUSTIFIED_AND_APPLIED
JUSTIFICATION = Gate A: four high-relevance counterfactuals share a missing capability vocabulary; the prior total-candidate cap also prevented later queries from running.
```

Patch details:

- Added capability-oriented templates: `AI coding agent workflow`, `spec driven development`, and `architecture visualization coding agent`.
- Moved the new templates before generic high-volume queries so they are not starved by `total_candidate_cap=20`.
- Kept request budget at `20`, per-query cap at `5`, total candidate cap at `20`, scoring weights, route semantics, and semantic threshold unchanged.
- No project names were added to discovery configuration.

Regression evidence:

```text
RECALL_DELTA = offline counterfactual target coverage 0/4 -> 4/4
NOISE_DELTA = offline sample noise 2 -> 2
REQUEST_BUDGET_DELTA = configured budget 20 -> 20; query templates 5 -> 8
LIVE_SMOKE_NOTE = one post-patch live run completed with SCAN_SUCCESS, 4 requests, 20 candidates, 0 failures; the first ordering saturated the 20-candidate cap before new templates ran, which motivated the ordering correction. The reordered patch is validated offline and will be observed on the next natural cycle.
```

## Library

```text
CAPABILITY_CARD_COUNT = 14
CODING_AGENT_WORKFLOW_SYNTHESIS = CREATED
```

Synthesis file: `library/generated/topics/CODING_AGENT_WORKFLOW_ENHANCEMENT.md`.

It groups reviewed evidence into project understanding, context/memory, specification/planning, agent workflow/harness, architecture visualization, skill/tool discovery, and long-term knowledge compilation. It is a derived human-readable projection; SQLite remains authoritative.

## Contextual Search

```text
CONTEXTUAL_SEARCH_VERIFICATION = PASS
```

Cases A-D (architecture visualization, specification-driven development, multi-agent workflow, and long-term technical knowledge) returned `MATCH`, each with at most three results. Case E (fix a typo in a known file) returned `NO_MATCH` after a minimal local-maintenance guard was added. The guard was test-driven: the new regression failed before implementation and passed afterward.

## Safety

```text
UNKNOWN_CODE_EXECUTION = NO
AUTO_RETRIEVE = YES
AUTO_ADOPT = NO
D:\money AUTO_MODIFICATION = NEVER
REAL_CROSS_PROJECT_USE_COUNT = 0
```

No candidate package, repository code, Skill, MCP, server, or service was executed. The Global Codex Skill remained unchanged and `CONTROLLED_PILOT_ACTIVE`.

## Verification

- 50 PTI tests passed.
- Python compilation passed.
- Capability Library rebuilt with 14 cards.
- Contextual search cases A-E passed the stated boundary.
- Formal Radar live smoke completed with Scheduler `Last Result=0`, `SCAN_SUCCESS`, four requests, 20 candidates, and zero failures.
- Automatic Chancellor processing remained successful; no active pending or locks remained after the audit.
- Scheduler cadence and hidden formal task actions were preserved.
- Git identity was not changed. The audit report and this round's source changes remain uncommitted if no repository-local identity is configured.

## Final Status

```text
TASK_STATUS = PASS
RUNTIME_STATUS = DEGRADED_HISTORY_ONLY
DISCOVERY_RECALL_STATUS = PATCHED_AND_OFFLINE_COUNTERFACTUAL_VALIDATED
CAPABILITY_LIBRARY_STATUS = EXPANDED
GLOBAL_SKILL_STATUS = CONTROLLED_PILOT_ACTIVE
PRODUCT_VALUE_STATUS = INSUFFICIENT_REAL_USE_EVIDENCE
FIRST_REAL_BLOCKER = NONE
NEXT_MODE = PASSIVE_REAL_TASK_REUSE_OBSERVATION
```

Stop here. Do not add automatic adoption, candidate installation, MCP, dashboard, vector database, capability graph, external-source platform, or usage-event infrastructure in this phase.
