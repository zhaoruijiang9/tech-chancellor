# Activation Execution Engine V1

## Why activation previously stopped

`process_activation_queue()` treated evidence that only an executor could create (pin, rollback, static review, isolated test, capability delta) as a prerequisite and immediately closed low-risk jobs as `FAILED_TERMINAL`. Stage B called that function synchronously after semantic review. No worker produced the missing evidence.

## New execution path

Stage B now only records the semantic decision and enqueues eligible activation work. The separate `activation-run` worker uses the existing activation queue/record tables, with a small additive queue migration for phase, contract and evidence. Pre-validation eligibility checks hazards; promotion eligibility is evaluated only after pinning, quarantine, static review, managed installation, rollback rehearsal, functional smoke and bounded comparison. Each phase is persisted and can be resumed with the same job and pinned source. Retries are capped at three. No long-running service was added.

The V1 automatic adapter is `READ_ONLY_MARKDOWN_INDEX`: a public GitHub snapshot is pinned and quarantined, but only its root README is copied into a versioned managed directory. The functional program is TechChancellor's own bounded local link search. No upstream script, package, plugin, MCP server, dependency installer or linked skill is run. Arbitrary Python/Node/CLI execution is not auto-enabled: this host has no OS-grade third-party execution sandbox, so such implementations require a human gate. The static result is explicitly limited to the data surface actually used; it is not a security certification of the entire archive.

`activation_records` owns execution lifecycle. Capability Intelligence `personal_states` is a projection of verified activation facts, including availability revocation on rollback. Historical terminal jobs, Archify, TradingAgents, backtesting-engine, BMAD and Spec Kit were not modified by the pilot.

## Real pilot

| Field | Observed result |
|---|---|
| System-selected candidate | `ComposioHQ/awesome-claude-skills` from the existing WATCHLIST |
| Selection reason | Read-only skill-source discovery adapter; no candidate code execution, account access, service or global install |
| Job | `activation_queue.id = 4`; `SUCCEEDED`, `AVAILABLE`, one attempt |
| Source pin | `be2a406907dbc61b73e6827ded415c96139d13a2` |
| Quarantine | Pinned GitHub archive; SHA-256 `88ab222afa22192da4aed413935fab9eee770bf49b80c51723acd634997ca251`; 2,049 archive entries bounded before reading |
| Static review | `PASS` for the root `README.md` data surface; 49 direct GitHub links indexed; upstream code not reviewed as executable and never run |
| Managed install | Pinned README only under `managed_capabilities/repo-1078079172/versions/<sha>/`; no dependencies |
| Rollback | Active-pointer write/restore rehearsed; previous-pointer receipt retained |
| Functional smoke | Local query `docx` returned one source link |
| Evaluation | Fixed queries `pdf`, `pptx`, `xlsx`: baseline 0 direct index links, candidate 3, new 3; `IMPROVED` for this narrow retrieval task only |
| Promotion | `TRIAL_ENABLED` / `AVAILABLE`; local `activation-search` returns pinned index links |
| Personal state | Implementation and `SKILL_ECOSYSTEM_DISCOVERY`: `VERIFIED`, `AVAILABLE` |
| Real use | Not claimed; `USED` remains absent |

The earlier semantic review judged the repository high-overlap and not proven better as a general skill ecosystem. This pilot does **not** overturn that broad judgment. It establishes only a local, repeatable way to retrieve three direct source links that PTI previously could not return through this adapter. Each linked project remains unreviewed and uninstalled.

The initial pilot pin was obtained through the already authenticated GitHub CLI. After review, the provider was changed to public `git ls-remote` with credential helpers and interactive prompts disabled; the same SHA was independently verified through that unauthenticated path. The archive fetch itself used public codeload HTTPS without candidate credentials.

## Verification and limits

- `python -m unittest discover -s tests`: 151 passed.
- `python -m compileall -q src run.py`: passed.
- Both PowerShell scheduler scripts parsed without errors; `git diff --check` passed.
- Re-running `activation-run` selected no additional candidate and did not repeat the download.
- `run_scheduled_activation.ps1` smoke completed with no duplicate work.
- Local production SQLite was backed up to ignored `state/intelligence.pre-activation-v1.db`; both source and backup passed integrity checks before the pilot.
- `D:\money` was not accessed, scanned, used as a benchmark or modified.
- No automatic upstream upgrade, GitHub push, tag movement, global package installation, broker access or credentialed candidate execution occurred.

Status: `ACTIVATION_ENGINE=PASS` for the supported read-only adapter; `FIRST_AUTONOMOUS_REAL_PILOT=PASS`; `NEW_AVAILABLE_CAPABILITY=1`; `NEW_USED_CAPABILITY=0`; `PERSONAL_STATE_SYNC=PASS`; `GENERIC_EXECUTABLE_TOOL_WORKER=NOT_ENABLED_WITHOUT_OS_SANDBOX`; `AUTO_UPGRADE=NO`; `D_MONEY=NOT_ACCESSED`.
