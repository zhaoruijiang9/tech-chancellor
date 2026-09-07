# Personal Codex Git Policy v0.1 and PTI History Report

Date: 2026-09-07

## Git Identity

```text
PERSONAL_GIT_NAME = 姜昭锐
PERSONAL_GIT_EMAIL = 307136752+zhaoruiji97-art@users.noreply.github.com
PTI_LOCAL_IDENTITY = CONFIGURED
GLOBAL_IDENTITY_MODIFIED = NO
```

The identity is configured only in the PTI repository. No global identity was created or changed.

## Policy

```text
GLOBAL_POLICY_LOCATION = C:\Users\25654\.codex\policies\development-policy.md
PROJECT_POLICY_OVERRIDE = docs/PERSONAL_CODEX_GIT_POLICY_OVERRIDE.md
PROJECT_CLASSIFICATION = PERSONAL
AUTO_COMMIT = YES
AUTO_PUSH = NO
```

The policy requires logical work-unit completion, relevant verification, diff review, precise staging, and secret/sensitive-file checks before automatic local commits. It prohibits automatic push, published-history rewrite, destructive reset over user work, and scheduled Git bots.

## History Audit

```text
START_HEAD = 342d996
UNCOMMITTED_STATUS_ENTRIES_BEFORE = 16
SENSITIVE_FILES_FOUND = NONE
REMOTE_CHANGED = NO
PUSH_PERFORMED = NO
```

The working tree contained code, tests, configuration, four capability reports, and the Archify trial material. Runtime state, quarantine evidence, downloaded archives, generated outputs, and dependency trees remain local and are ignored. PTI-owned Archify manifests, wrappers, and pinned source metadata are versioned; the full third-party tree is not.

## Commits Created

| SHA | Message | Purpose |
| --- | --- | --- |
| `3257539` | `chore: establish PTI git hygiene boundaries` | Add PTI project classification and runtime/quarantine ignore boundaries. |
| `0889d23` | `fix: ensure fair discovery query execution` | Prevent configured discovery queries from being starved by early caps and extend capability search/library evidence. |
| `f69e47a` | `feat: add safe capability activation policy` | Add tiered activation policy, queue persistence, real-use evidence, and Stage B integration. |
| `689119a` | `docs: record capability activation decisions` | Preserve the recent capability and activation reports in readable project history. |
| `be88212` | `feat: record controlled Archify trial metadata` | Version PTI-owned Archify manifests and wrappers without committing dependencies or runtime artifacts. |
| final report commit | `docs: record personal git policy and history audit` | Record the policy, audit evidence, final runtime state, and future commit boundaries. |

## Final State

```text
END_HEAD = final report commit (tip of `master` at completion)
WORKTREE_STATUS = CLEAN (ignored local runtime state remains)
TEST_STATUS = PASS, 65 tests
COMPILE_STATUS = PASS
PTI_RUNTIME_STATUS = DEGRADED_HISTORY_ONLY (legacy duplicate history preserved)
PENDING = 0
LOCKS = ABSENT
SCHEDULER = PTI-Radar-Scan Ready; PTI-Chancellor Ready
ARCHIFY_STATUS = TRIAL_ENABLED / GLOBAL_CODEX_CONTROLLED / TESTED
```

The historical `DEGRADED_HISTORY_ONLY` condition was preserved as required. No database cleanup or product-semantic change was performed.

## Future Behavior

For confirmed `PERSONAL` repositories, Codex may configure the confirmed local identity and create a local commit after a completed, verified, isolated logical work unit. Codex will not push automatically. Git commits are part of the development workflow, not a Windows scheduled task.

## Publication

GitHub publication, remote configuration, release creation, and push were not performed. A separate pre-publication audit remains required before any future public release.
