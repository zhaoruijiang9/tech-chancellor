# PTI Global Codex Skill Controlled Pilot v0.1

Date: 2026-09-02
Project: `D:\personal-tech-intelligence`
Boundary: independent technology-intelligence system; `D:\money` was not read or modified.

## Final Status

```text
TASK_STATUS = PASS
RUNTIME_STATUS = NOT_EVALUATED
SKILL_STATUS = CONTROLLED_PILOT_ACTIVE
PRODUCT_VALUE_STATUS = INSUFFICIENT_REAL_USE_EVIDENCE
FIRST_REAL_BLOCKER = NONE
NEXT_MODE = PASSIVE_REAL_TASK_REUSE_OBSERVATION
```

This pilot proves the controlled retrieval path and safety boundaries. It does not prove that any candidate project should be installed, adopted, or connected to a trading workflow.

## Capability-Card Readiness

The library contained 10 `REVIEWED` cards at inspection time. Each card had repository identity, problem solved, user relevance, existing-capability comparison, capability delta, evidence maturity, consumption form, authorization boundary, semantic action, route, limitations, timestamp, and popularity metadata.

Focused cards:

| Repository | Practical reading | Boundary |
|---|---|---|
| `headroomlabs-ai/headroom` | Possible context compression for agent output and RAG evidence | `WATCH`; claims and operational behavior remain unverified |
| `volcengine/MineContext` | Context-aware assistant pattern using memory and retrieval | `WATCH`; metadata-only evidence, no adoption |
| `nieledran/backtesting-engine` | Quant research and portfolio backtesting reference | `CANDIDATE_FOR_QUARANTINE`; user approval required before any tool action |
| `chunkhound/chunkhound` | Repository mapping and semantic code search reference | `REFERENCE_ONLY`; possible overlap and MCP/data-boundary risk |

Additional cards were retained as read-only references for `cased/kit`, `ComposioHQ/awesome-claude-skills`, `gmickel/flow-next`, `FoundationAgents/MetaGPT`, `langchain-ai/langchain`, and `TauricResearch/TradingAgents`. No card was installed or executed.

Readiness: `PASS_FOR_READ_ONLY_RETRIEVAL`; not sufficient evidence for deployment or adoption.

## Global Skill

The user-level Skill is enabled by placement in the active Codex user skill root:

```text
C:\Users\25654\.codex\skills\personal-tech-intelligence\SKILL.md
C:\Users\25654\.codex\skills\personal-tech-intelligence\scripts\search_capabilities.ps1
C:\Users\25654\.codex\skills\personal-tech-intelligence\agents\openai.yaml
```

The adapter calls only the existing command `D:\personal-tech-intelligence\run.py search-capabilities`. It does not open SQLite directly, inspect a caller repository, persist prompt context, install or execute candidates, enable MCP, start a service, or modify another project. `D:\money` is accepted only as a metadata label and was not accessed.

Policy: `AUTO_RETRIEVE=YES`; `AUTO_ADOPT=NO`; `AUTO_INSTALL=NO`; `AUTO_EXECUTE=NO`; `AUTO_CLONE=NO`; `ENABLE_MCP=NO`; `START_SERVICE=NO`; `MODIFY_OTHER_PROJECT_FROM_PTI=NO`.

SHA-256:

```text
SKILL.md = BE7A22931AB6098437E92F33D2490E7BF99D803CF926CA8A4E21237927423E82
scripts/search_capabilities.ps1 = D1A675FC0016C8C003DB3AEC78310191DDF9BF617C244DD8754DF107AE1B5FF0
agents/openai.yaml = 717B713A78EE7D8642D92F66DB94BCB2B75E37250A01CC6DB9E7B229CDFCA288
```

## Explicit Retrieval Evidence

Seven relevant technical queries returned `MATCH` using short English technical keywords:

1. semantic code search for a large repository
2. compress verbose AI agent tool output and logs
3. cross-session memory and context retrieval for an AI assistant
4. quantitative strategy backtesting and portfolio research
5. multi-agent software research and workflow coordination
6. repository mapping and symbol extraction for coding agents
7. AI context engineering and RAG retrieval

Relevant retrieval: `7/7 MATCH`.

Three irrelevant queries returned `NO_MATCH`: typo correction, deterministic list sorting, and showing Git status. Supplemental Chinese-only phrasing produced several `NO_MATCH` results; this is a known retrieval-quality limitation, not a safety failure. The Skill keeps such failures non-blocking and does not invent a match.

## Implicit-Trigger Smoke

Controlled smoke cases were assessed against the Skill description and exclusion boundary:

| Case group | Cases | Expected trigger | Result |
|---|---:|---:|---:|
| relevant | large-repository context, code search, log compression, cross-session continuity, quant backtesting | 5 | 5 |
| irrelevant | typo, rename, deterministic local bug, arithmetic, local formatting | 0 | 0 |

Observed smoke result: `5/5` relevant trigger decisions and `0/5` irrelevant false positives in this controlled pass. This is a policy/behavior smoke test, not evidence of product value from long-term autonomous use.

## Safety and Runtime

- Explicit adapter calls were read-only and left PTI state unchanged.
- No candidate repository was cloned, installed, imported, executed, or connected to MCP.
- No trading action, broker action, `D:\money` read, or `D:\money` write occurred.
- Existing PTI scheduled radar and Chancellor tasks were not changed.
- Failure and `NO_MATCH` remain non-blocking.
- `REAL_CROSS_PROJECT_USE_COUNT=0`.

Verification completed after the Skill was created: Skill structural validation, adapter invocation, 10 retrieval cases, full PTI test suite, Python compilation, health check, and scheduled-task inspection. The current health result is `NOT_EVALUATED` because the existing latest radar run has `TASK_LAST_RESULT_NONZERO` / `SCAN_NOT_EVALUATED`; the Skill itself introduces no new blocker.

## Stop Point

The controlled pilot is complete. Do not add automatic adoption, candidate installation, background polling, MCP integration, vector storage, or a dashboard in this phase. The next mode is passive observation of real tasks and reuse evidence.
