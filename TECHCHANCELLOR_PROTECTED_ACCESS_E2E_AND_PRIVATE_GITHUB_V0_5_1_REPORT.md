# TechChancellor protected access E2E and private GitHub audit v0.5.1

审计日期：2026-09-09

## 授权链

- `PROTECTED_ACCESS_MODEL = DEFAULT_DENY_PLUS_TASK_SCOPED_READONLY`
- `OLD_HARD_DENY_LOCATION = run_archify.ps1 输入校验；已替换为受保护目标授权校验。全局 Archify Skill 仍保留禁止 D:\money 的高优先级保护规则。`
- `E2E_AUTHORIZATION_WIRING = wrapper TargetProjectPath + AuthorizationPath + external snapshot output`
- `NO_AUTH_TEST = PASS, exit 78`
- `VALID_AUTH_TEST = PASS, exit 0, Archify 9/9, artifact created`
- `WRITE_DENY_TEST = PASS, Python policy test`
- `EXPIRED_AUTH_TEST = PASS, exit 78`
- `DEFAULT_AFTER_TASK = DENY`

真实 wrapper E2E 使用隔离临时保护目录完成，没有读取 `D:\money`。一次性任务授权收据只存在临时目录，没有进入 Git。

## Money 交付

- `MONEY_START_HEAD = NOT_READ`
- `MONEY_END_HEAD = NOT_READ`
- `MONEY_TASK_DIFF = NOT_VERIFIED`
- `MONEY_READ = NOT_PERFORMED`
- `MONEY_WRITE = NO`
- `SANITIZED_SNAPSHOT = NOT_CREATED`
- `ARCHIFY_MONEY_USE = NOT_PERFORMED`
- `MONEY_DIAGRAMS = NOT_GENERATED`
- `ROOT_ENTRY = D:\项目架构图\总目录.html`

原因：当前受控 Archify Skill 的明确规则仍禁止访问 `D:\money`。本轮没有修改该高优先级保护规则，也没有通过其它工具绕过它，因此不能宣称 Money 架构交付完成。

## Private GitHub 历史审计

- `REACHABLE_COMMITS_SCANNED = 12`
- `CURRENT_TREE_SECRET_SCAN = PASS, no credential-pattern files found`
- `FULL_HISTORY_SECRET_SCAN = PASS, 0 credential-pattern hits`
- `HIGH_SENSITIVITY_PERSONAL_DATA = NOT_FOUND_BY_BOUNDED_PATTERN_SCAN`
- `MACHINE_PATHS_FOUND = 241 history references`
- `PRIVATE_REPO_PRIVACY_NOTES = historical reports contain local project/user paths and internal development history`
- `GITHUB_PRIVATE_READINESS = READY_WITH_PRIVACY_NOTES`
- 未发现 token、私钥、Bearer 凭据、GitHub token、API key 或高风险凭据文件名；本轮没有输出疑似敏感值，也没有重写历史。

## 当前状态

- `TASK_STATUS = PARTIAL_WITH_PROTECTED_BOUNDARY`
- `PROTECTED_ACCESS_E2E = PASS_ON_ISOLATED_PROTECTED_ROOT`
- `MONEY_ARCHITECTURE_STATUS = BLOCKED_BY_CURRENT_ARCHIFY_SKILL_RULE`
- `MONEY_INTEGRITY_STATUS = NO_WRITE_OR_EXECUTION_PERFORMED; HEAD_NOT_READ`
- `ARCHIFY_STATUS = PTI_USED; PROTECTED_ROOT_E2E_PASS`
- `GITHUB_PRIVATE_READINESS = READY_WITH_PRIVACY_NOTES`
- `PUBLIC_V0_1_READINESS = NOT_YET`
- `FIRST_REAL_BLOCKER = D:\money access conflicts with current high-priority Archify Skill rule`
- `NEXT_MODE = resolve protected-capability rule precedence before Money read-only snapshot`

## 验证

- 完整测试：`72/72 PASS`
- 编译检查：`PASS`
- wrapper PowerShell 语法解析：`PASS`
- PTI 健康检查：两个任务 Ready、无 pending；保留历史重复记录告警。
- 本轮未调用 Radar、未修改交易系统、未 push、未创建 GitHub remote。
