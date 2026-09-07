# PTI Git Policy Override

This repository is the first confirmed pilot of `PERSONAL_CODEX_GIT_POLICY_V0.1`.

```text
REPOSITORY_CLASS = PERSONAL
AUTO_COMMIT = YES
AUTO_PUSH = NO
```

The repository-local Git identity is the user's confirmed GitHub noreply identity. PTI runtime state, downloaded source archives, quarantine evidence, dependency trees, and generated outputs remain local unless a future project decision explicitly promotes a reproducible artifact into source control.

This override records PTI-specific facts only. The full behavior is inherited from the user-level policy at `C:\Users\25654\.codex\policies\development-policy.md`.
