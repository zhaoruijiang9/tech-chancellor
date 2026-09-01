# PERSONAL_TECH_INTELLIGENCE_SIGNAL_QUALITY_BASELINE_V0_1

**As of:** 2026-08-27  
**Status:** `SIGNAL_QUALITY_STATUS = INSUFFICIENT_SAMPLE`

## 1. Current Sample Size

- Unique repositories in SQLite ledger: **20**.
- Latest report visible items: **5** (`HIGH_PRIORITY=5`, `secondary=0`), due to the configured report limit.
- Real semantic Chancellor decisions: **3**.
- User feedback records: **0**.
- Active pending packets at measurement time: **0**.
- This is an early operational sample, not a quality benchmark. It is too small for global scoring calibration.

## 2. Deterministic Prefilter and Action Distribution

The ledger contains 20 discovered identities. Seventeen still have the deterministic `USER_REVIEW_RECOMMENDED` state; three have since been replaced by real semantic outcomes of `REFERENCE_ONLY`. The three semantic outcomes are:

| Action | Count |
|---|---:|
| `REFERENCE_ONLY` | 3 |
| `WATCH` | 0 |
| `IGNORE` | 0 |
| `HIGH_PRIORITY` / user review outcome | 0 semantic decisions |

The latest report is a pre-Chancellor view and contains five `USER_REVIEW_RECOMMENDED` / `HIGH_PRIORITY` items. It must not be combined with the semantic action counts as though they were the same decision layer.

## 3. Route and Source Distribution

Unique ledger routes:

| Route | Count |
|---|---:|
| `AI_AGENT` | 10 |
| `AI_EXPERIENCE` | 5 |
| `QUANT_DATA` | 5 |
| `PRODUCTIVITY` | 0 observed candidates |

The configured discovery source contains four query groups: `AI_AGENT`, `AI_EXPERIENCE`, `QUANT_DATA`, and `PRODUCTIVITY`. The ledger shows coverage for the first three, but does not preserve a durable per-query identifier, so exact query-level recall cannot be calculated. No `MONEY_TRADING` route was produced by the current sample.

Enrichment degradation was frequent in the semantic sample: the three real Chancellor packets recorded README, release, commit, and tree enrichment failures, chiefly HTTP 403. This makes the current semantic conclusions conservative but also limits capability comparison.

## 4. Representative Decisions

### Positive early signal, not yet validated

- `lnptuonli/Quantification-Researching-Platform` — 21 stars, `QUANT_DATA`.
- `nieledran/backtesting-engine` — 16 stars, `QUANT_DATA`.
- `cased/kit` — 1,311 stars, `AI_EXPERIENCE`.

These are useful recall examples because the system did not require high popularity to retain them. They are not yet proven good recommendations: none has a real semantic decision or user feedback.

### Low-value semantic decisions

- `langchain-ai/langchain` — `REFERENCE_ONLY + AI_AGENT`; high duplication with Codex skills, MCP/plugins, and the existing agent project; no verified incremental capability.
- `FoundationAgents/MetaGPT` — `REFERENCE_ONLY + AI_AGENT`; role-based multi-agent orchestration overlaps existing capabilities and no active unmet need was evidenced.
- `TauricResearch/TradingAgents` — `REFERENCE_ONLY + AI_AGENT`; trading relevance was acknowledged, but no safe, verified production delta was shown. The route identifies the next review domain and does not authorize connection to `D:\money`.

These are valid semantic outcomes, not failures. They show the Chancellor can suppress famous but weakly differentiated projects after review, while also showing that the current prefilter may spend expensive review capacity on famous baseline projects.

## 5. Potential False Positives

`POTENTIAL_FALSE_POSITIVE_SET`:

- LangChain, MetaGPT, and TradingAgents were all high-visibility, high-duplication, low-proven-need projects that reached semantic review and all became `REFERENCE_ONLY`.
- This is only one repeated acceptance/scan family, not enough evidence for a blacklist or scoring change. The current explanation is consistent with deliberate acceptance cases plus repeated scanner output; production pollution is not yet proven.

## 6. Potential False Negatives

`POTENTIAL_FALSE_NEGATIVE_CANDIDATE_SET`:

- The low-star `QUANT_DATA` candidates above are retained in the ledger, but their actual capability delta is unknown.
- No candidate currently has both a verified high current-need match and a verified real increment, so no false negative can be confirmed.
- Keep these identities as observation cases for later semantic review or user feedback; do not globally increase low-star weight yet.

## 7. Capability Delta Quality

Classification of the three real semantic decisions:

| Candidate family | Classification | Evidence |
|---|---|---|
| LangChain / MetaGPT | `HIGH_DUPLICATION` | Chancellor explicitly compared against Codex skills, MCP/plugins, and the existing agent project. |
| TradingAgents | `PARTIAL_INCREMENT` but not adoption-worthy | Finance-specific multi-agent orchestration is a plausible delta, but data, reliability, safety, and production evidence were unavailable. |

The decisions use the local capability profile more specifically than a generic “other AI tools” statement. However, the profile still contains several `UNKNOWN` entries, and the current sample has no confirmed `REAL_INCREMENT`. Capability Delta quality is therefore `PARTIAL`, not validated.

## 8. AI_EXPERIENCE Recall

The profile and query configuration explicitly cover context engineering, memory, semantic search, and local search as the intended domain. Five `AI_EXPERIENCE` identities are present in the ledger, including context and local-context projects. However, all three semantic reviews were `AI_AGENT`; there is no semantic-quality sample for `AI_EXPERIENCE`.

Assessment: `RECALL_SIGNAL_PRESENT_BUT_QUALITY_UNVALIDATED`. The current data does not justify changing queries or prefilter rules.

## 9. Routing Quality

Observed routing is internally consistent for the three semantic decisions: all are `AI_AGENT` because the next useful review concerns agent architecture and capability overlap. TradingAgents is not treated as approval for `D:\money`; no money-system artifact was created.

The remaining risk is conceptual: `AI_AGENT` can absorb finance-oriented agent projects when the next review should be independent trading-system or quantitative review. The current TradingAgents reasoning records the finance angle and the missing production evidence, so this is not a confirmed routing bug. More examples are required before introducing a new route or rule.

## 10. Noise Assessment

- Latest visible report: 5 items, all `HIGH_PRIORITY` at the deterministic layer.
- Semantic review yield: 0 adoption-worthy outcomes out of 3; 3 `REFERENCE_ONLY`.
- User-visible signal rate cannot be calculated because no notification events or user feedback records exist.
- Early noise concern: deterministic fame/relevance scoring can promote broad, popular agent frameworks despite high duplication. This is a calibration candidate, not yet a proven production regression.

## 11. Evidence Limitations

- Only 20 unique ledger identities and 3 semantic decisions exist.
- User feedback is absent, so usefulness, wrong-route, and reading-cost claims are unvalidated.
- Enrichment failures prevent detailed code, release, dependency, and feature comparisons.
- Inbox filenames are reused by repository identity and are not a complete immutable historical event log; the SQLite ledger and current artifacts are the authoritative available sample.
- Query-level attribution and notification delivery history are not persisted in the current sample.

## 12. Evidence-Backed Next Improvements

1. Continue scheduled observation without changing deterministic weights.
2. Preserve the low-star quant and AI_EXPERIENCE identities as explicit observation cases.
3. Collect real user feedback using the existing labels before calibration.
4. Track whether the same high-duplication baseline repositories repeatedly consume semantic review across multiple independent scans.
5. Reassess `AI_EXPERIENCE` only after it has several semantic decisions, not from ledger presence alone.
6. Keep `MONEY_TRADING` as an independent-review route only; it never authorizes access to `D:\money`.

## Final Quality Checkpoint

`REAL_EVIDENCE_BEFORE_CALIBRATION = REQUIRED`

`SIGNAL_QUALITY_STATUS = INSUFFICIENT_SAMPLE`

No scoring, routing, infrastructure, notification, or execution changes are justified by the current sample.
