# PTI Autonomous Low-Risk Activation v0.2

## 1. Starting State

The prior fairness work remains closed and was not changed: 8/8 query first-pass, 8 requests, 40 raw observations, 40 unique repositories, 20 final candidates, 0 source failures. The observed runtime remains `DEGRADED_HISTORY_ONLY` only because legacy duplicate decision history is preserved; locks, pending packets, and both formal tasks are healthy.

Archify started as `ISOLATED_TEST_PASS / TESTED`, with no managed capability area and no Codex consumption path.

## 2. Activation Policy

`config/capability_activation_policy.json` is the machine-readable source of truth. The policy returns tier, allowed automatic actions, human gates, prohibitions, maximum state, and explainable reason codes.

- TIER 0: knowledge/pattern reference; automatic read, comparison, and pattern promotion; no execution.
- TIER 1: declarative Skill; quarantine, static analysis, isolated test, and controlled trial when all gates pass.
- TIER 2: low-privilege local tool; isolated install/test and controlled trial when pinned, reversible, and free of credentials, admin, service, listener, system, PATH, and browser-extension requirements.
- TIER 3: static analysis or human gate only.
- TIER 4: trading, broker, account, privileged, credential, or `D:\money` scope; human approval or prohibition.

The SQLite `activation_records` table is authoritative. `activation_queue` is a small idempotent queue with `PENDING`, `PROCESSING`, `SUCCEEDED`, `RETRYABLE`, `BLOCKED_HUMAN`, and `FAILED_TERMINAL` semantics. Chancellor semantic success is not downgraded by activation failure.

## 3. Archify Deployment

- Repository: `tt-a1i/archify`, id `1211139949`
- Pinned commit: `c6519401f7b91b9d43011657880893b0a8955548`
- Managed location: `D:\personal-tech-intelligence\managed_capabilities\archify`
- Dependency install: isolated version directory, lockfile-aware, `--ignore-scripts`; no global install or PATH change.
- Lock hash: `f875c29b190f6f5dc14bea7e56879ad2282c0a5212253b24937f77b4f6198054`
- Wrapper: `wrappers/run_archify.ps1`; fixed entrypoint, explicit paths, timeout, output containment, D:\money rejection, update check disabled, browser open disabled, and structured receipts.
- Control: `wrappers/set_trial_state.ps1`; disable returned exit 78 and re-enable returned exit 0.
- Trial: `TRIAL_ENABLED`, evidence maturity `TESTED`, availability `GLOBAL_CODEX_CONTROLLED`, real use `NO`.

Acceptance evidence:

- Fixture A: architecture delivery, exit 0, 9/9 checks, 0 errors, 0 warnings.
- Fixture B: independent small architecture delivery, exit 0, 9/9 checks, 0 errors, 0 warnings.
- Fixture C: before/after delta, exit 0, both compositions pass, 2 components and 2 connections identified as added.
- No browser, persistent process, credential, system service, PATH, registry, or `D:\money` access occurred.

## 4. Automatic Activation Path

After a valid Chancellor decision:

1. TIER 0 is automatically promoted to `ACTIVE_PATTERN`.
2. TIER 1/TIER 2 are classified and placed in the SQLite activation queue for bounded quarantine/static/test processing.
3. TIER 3/TIER 4 are recorded as `BLOCKED_HUMAN` or prohibited.
4. A failed activation remains separate from `CHANCELLOR_SUCCESS`.

The current sweep queued two TIER 2 candidates for future bounded processing (`coleam00/archon`, `nieledran/backtesting-engine`) and auto-promoted the eligible reference/pattern cards. No additional candidate was installed or enabled in this cycle.

## 5. Existing Capability Sweep

| Result | Count | Meaning |
|---|---:|---|
| `ACTIVE_PATTERN` | 10 | Reference/pattern use is available without code execution |
| `TRIAL_ENABLED` | 1 | Archify, controlled wrapper only |
| `QUARANTINE_READY` / queued | 2 | TIER 2 candidates awaiting bounded evidence |
| `BLOCKED_HUMAN` | 1 | TradingAgents, TIER 4 |

The generated library now exposes tier, activation state, availability, safe invocation, pinned version, test status, and rollback status for all 14 cards.

## 6. Tests and Runtime

- Full PTI test suite: 65 tests passed after implementation.
- `compileall`: verified.
- Activation policy, state transitions, queue idempotency, real-use guard, search availability, and library rebuild tests: verified.
- Managed wrapper acceptance: A/B/C passed; disable/enable rollback passed.
- Scheduler count remains two: `PTI-Radar-Scan` and `PTI-Chancellor`; no third task added.
- Pending packets: 0; locks: absent; latest Radar: `SCAN_SUCCESS`, 8 requests, 20 final candidates.

## 7. Safety

`UNKNOWN_UNCONTROLLED_EXECUTION` remains prohibited. Only the pinned, quarantined, statically reviewed Archify version was executed in a PTI-managed directory. The wrapper rejects `D:\money`, arbitrary commands, browser opening, persistent preview, and uncontained output. `USED` can only be recorded through explicit real-task evidence; fixture success cannot manufacture it.

## Final Status

```text
TASK_STATUS = PASS_WITH_CONTROLLED_TRIAL
RUNTIME_STATUS = DEGRADED_HISTORY_ONLY
DISCOVERY_STATUS = FAIRNESS_PRESERVED
ACTIVATION_POLICY_STATUS = PRODUCTION_READY_V0_2
AUTONOMOUS_LOW_RISK_ACTIVATION = ENABLED_WITH_TIER_GATES
ARCHIFY_STATUS = TESTED_AND_CONTROLLED_TRIAL_ENABLED
ARCHIFY_CODEX_AVAILABILITY = PASS
CAPABILITY_LIBRARY_STATUS = ACTIVATION_AWARE_14_CARDS
GLOBAL_PTI_SKILL_STATUS = CONTROLLED_PILOT_ACTIVE_WITH_TRIAL_CONSUMPTION
REAL_USE_STATUS = AWAITING_NATURAL_TASK
PRODUCT_VALUE_STATUS = CONTROLLED_CAPABILITY_VALUE_VALIDATED_REAL_USE_PENDING
FIRST_REAL_BLOCKER = NONE_FOR_ARCHIFY; FUTURE_TIER2_REQUIRES_CANDIDATE_SPECIFIC_EVIDENCE
NEXT_MODE = AUTONOMOUS_LOW_RISK_ACTIVATION_PLUS_PASSIVE_REAL_USE
ADDITIONAL_AUTO_ACTIVATION_COUNT = 0
GIT_COMMIT_STATUS = BLOCKED_BY_IDENTITY_CONFIGURATION
```
