# TechChancellor Public v0.1 Final Engineering Hardening v0.7.1

## Scope

This report covers the public v0.1 engineering hardening pass for `D:\personal-tech-intelligence`. It does not change `D:\money`, the Radar/Chancellor design, Archify policy, or GitHub visibility. No push was performed.

## Decision

`READY_EXCEPT_OWNER_DECISIONS`

No engineering blocker remains in the audited public path. Publication still requires owner decisions on the repository license, public visibility, and the timing of Issues/Discussions and any release tag.

## Engineering Changes

- Added an idempotent `python run.py init` command that validates the shipped JSON inputs, creates local runtime directories, and initializes SQLite.
- Made `health` return a structured `NOT_INITIALIZED` result when the database is absent instead of crashing.
- Scoped scheduled-task health failures to tasks whose action actually points at the project being checked. This prevents a clean clone from inheriting the health result of another checkout on the same Windows host.
- Removed machine-specific Codex executable and repository-root literals from the two Codex smoke `.cmd` files. They now use `%~dp0`, `%USERPROFILE%`, and optional `PTI_CODEX_EXE`.
- Replaced the tracked local capability profile's user/project-specific descriptions with generic public-safe wording.
- Removed the tracked personal `MY_CAPABILITIES.md`; it is now generated locally and ignored.
- Updated English and Chinese quickstarts with the clean-install flow and the fact that no third-party Python package is required.

## Verification

- Unit tests: `74` passed.
- Python compilation: passed for `src` and `run.py`.
- Diff whitespace check: passed.
- Fresh local clone smoke: `init=0`, `health=0`, `build-library=0`, `my-capabilities=0`; SQLite created; generated capability output remained ignored.
- Initialization was tested twice against the same temporary root; the second run created no new directories.
- Current worktree: clean at report creation.

The host's existing scheduled tasks have historical non-zero results when checked against `D:\personal-tech-intelligence`; this remains a local runtime observation, not a clean-install failure. The clean-clone health check ignores those unrelated task actions as intended.

## Portability Audit

Active runtime code derives the project root from `run.py` or receives it as an argument. Codex executable discovery uses `PTI_CODEX_EXE` and the current user's profile. Scheduler scripts use `%~dp0` / `$PSScriptRoot`. The only retained `D:\money` reference in active code is an intentional protected-root safety guard, not a machine binding.

Tracked historical reports may mention development-machine paths. They are documentation evidence, not runtime configuration; the current public-facing quickstart and active profile no longer require those paths.

## History Integrity Audit

The repository contains `21` local commits on the current branch. The meaningful transitions were preserved as separate commits, including:

- `0889d23` — fair discovery query execution fix;
- `f69e47a` — safe capability activation policy;
- `e1cce97` — task-scoped protected access and TechChancellor branding;
- `0a5a543` — public contact and feedback policy.

The relevant discovery, activation-policy, and test files are present at each audited transition and compile successfully from archived commit trees. No history rewrite or force operation was performed.

## Current Tree Privacy Audit

No private key or common API-token pattern was found in the current non-document tracked tree. The approved public contact `2565455406@qq.com` is intentionally present in the README and contribution guidance and is not treated as a blocker. Credentials, verification codes, passwords, account recovery information, and the generated personal capability report are not part of the intended public tree.

Archify's explicit protected-root refusal for `D:\money` remains a safety rule and is not a disclosure of trading data.

## Git State and Publication Boundary

- Branch: `master`
- Local HEAD: `610f4553739aca07e7a45f44866922c901daf4a4`
- Remote: `https://github.com/zhaoruijiang9/tech-chancellor.git`
- Ahead/behind versus `origin/master`: `4/0`
- Push performed: `NO`
- Automatic push policy: `NO`

The local commits are intentionally left for owner review. Git author identity remains separate from the approved public contact email. Exact new-account GitHub noreply cleanup is not a publication blocker.

## License Analysis

No root `LICENSE` file is currently present, so this is an owner decision before a public release:

- **MIT**: shortest and most familiar permissive license; simplest adoption story.
- **Apache-2.0**: permissive license with an explicit patent grant and more detailed conditions; recommended for a technical system intended for reuse.

Recommendation: choose Apache-2.0 unless the owner prefers MIT's minimal text. No license file was created in this pass.

## Remaining Owner Decisions

1. Choose and add the root license.
2. Decide when to change GitHub visibility from private to public.
3. Enable Issues and Discussions at the public-release point.
4. Decide whether to create a version tag after the final owner review.

## Contact and Feedback Status

- `PUBLIC_CONTACT_EMAIL=2565455406@qq.com`
- `PUBLIC_CONTACT_STATUS=USER_APPROVED`
- `ISSUES_FEEDBACK=PLANNED_FOR_PUBLIC_RELEASE`
- `DISCUSSIONS_FEEDBACK=PLANNED_FOR_PUBLIC_RELEASE`
- `GIT_NOREPLY_BLOCKS_PUBLICATION=NO`
