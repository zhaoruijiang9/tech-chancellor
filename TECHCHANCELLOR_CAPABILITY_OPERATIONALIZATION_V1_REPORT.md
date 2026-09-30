# TechChancellor Capability Operationalization V1

## 结论

`SKILL_ECOSYSTEM_DISCOVERY` 已由正式 Radar 消费，首次形成有证据的 `AVAILABLE -> USED`。真实来源是固定版本的 `ComposioHQ/awesome-claude-skills` 只读索引；Radar 没有运行第三方脚本，也没有把索引中的项目视为可信或自动安装。

本轮有效链路：`scan:133be1cc150b` -> 索引检索 -> GitHub 仓库身份还原 -> 与原有 GitHub 发现结果去重 -> 全局候选排序与一个高优先级来源评审位 -> 仓库 README 取证 -> 原有本地语义评审。进入处理的新增项目为 [`NeoLabHQ/context-engineering-kit`](https://github.com/NeoLabHQ/context-engineering-kit)，GitHub repository ID `1096085345`。该项目仍是**未信任的新候选**；本轮没有为它创建可用 implementation、运行其代码或启动激活。

这里的“语义评审”是现有 `LocalSemanticChancellor` 的本地证据规则，不等于 Codex Stage B 的最终 Chancellor 决策。该项目目前没有 Stage B pending packet；这一点不应被描述为完整的候选激活闭环。

## 真实运行与纠错

| 扫描 ID | 索引链接 | 规范化仓库 | 新线索 | 进入处理 | 本地语义评审 | Material use |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `22888e76006d` | 5 | 4 | 2 | 1 | 0 | 否；没有完成后续评审 |
| `a2123370f1c5` | 5 | 4 | 2 | 1 | 1 | 否；误入的家谱研究主题与当前需求不符，已撤回误记的 USED |
| `133be1cc150b` | 5 | 4 | 2 | 1 | 1 | 是；`context-engineering-kit` 经 README 取证后完成本地语义评审 |

三次扫描均为 `SCAN_SUCCESS`，每次总候选 20、主扫描失败 0。第二次调用的原始观测保留供审计；仅纠正本轮写入的 `material_use`、USED 投影和激活记录。纠错前已使用 SQLite 在线备份保存数据库快照。新意图规则将普通“research”与量化/金融研究区分，并要求实际 README 证据；无效结果不再晋级。

调用记录保留 capability、implementation、consumer、scan ID、意图、计数、下游仓库 ID、成败与 material 标记。Dashboard 可见使用方、最近真实使用、结果和连续失败数；目前连续失败为 0。固定预算为每次最多 10 条索引原始链接、5 个规范化仓库、3 次元数据查询、2 个新候选、1 个公平评审位；原 Radar 候选上限 20、GitHub 请求预算 23 均仍生效。来源失败为 fail-soft，不会将整个 Radar 误报失败。

## 当前库的 Activation Readiness

审计对象为正式库中全部 12 个非 USED implementation。Readiness 是独立于 activation state 的判断；已有 `Archify` 和本轮 `awesome-claude-skills` 为 USED，不在下表中。

| Implementation | Readiness | 当前实际阻断 |
| --- | --- | --- |
| FoundationAgents/MetaGPT | NO_MEANINGFUL_DELTA | 编排能力重叠，缺少明确未满足需求 |
| TauricResearch/TradingAgents | HUMAN_GATE | 既有人工决策未解除；金融 Agent 不自动试点 |
| bmad-code-org/BMAD-METHOD | NO_MEANINGFUL_DELTA | 知识参考，方法采用证据不足 |
| cased/kit | NO_MEANINGFUL_DELTA | 相比本地检索的优势未证实 |
| chunkhound/chunkhound | REQUIRES_OS_SANDBOX | 持久索引/MCP 执行需安全隔离，增益也待验证 |
| coleam00/archon | REQUIRES_OS_SANDBOX | 保留 VALIDATION_FAILED；运行与回滚证据不足 |
| github/spec-kit | NO_MEANINGFUL_DELTA | 知识参考，完整工作流无已证实优势 |
| gmickel/flow-next | NO_MEANINGFUL_DELTA | 跨 Agent 工作流增益未证实 |
| headroomlabs-ai/headroom | REQUIRES_OS_SANDBOX | 代理/MCP 将执行第三方代码并处理任务上下文 |
| langchain-ai/langchain | NO_MEANINGFUL_DELTA | 没有明确增量能力或当前本地阻断 |
| nieledran/backtesting-engine | HUMAN_GATE | 维持 APPROVED_WAITING_VALIDATION；交易/凭证边界未解除 |
| volcengine/MineContext | REQUIRES_OS_SANDBOX | 桌面上下文采集需要隔离与隐私控制 |

`SECURE_THIRD_PARTY_EXECUTION_SANDBOX` 已以 `MISSING_CAPABILITY` 记录为平台缺口。本轮没有用 Python venv 冒充 OS 隔离，也没有新增可执行第三方 worker。没有对象满足第二个低风险自动 Pilot 的全部条件，故 `SECOND_PILOT=NO`。

## 数字与边界

```text
AVAILABLE_CAPABILITIES = 2 (含已使用的能力)
USED_CAPABILITIES = 2
PRODUCTION_CONSUMER_BINDINGS = 1
REAL_CAPABILITY_INVOCATIONS = 3
MATERIAL_REAL_USES = 1
NEW_CANDIDATES_FROM_CAPABILITY = 1 (进入本地语义评审并形成真实使用证据)
READY_WITH_EXISTING_ADAPTER = 0 (非 USED 库)
NEEDS_SAFE_ADAPTER = 0
REQUIRES_OS_SANDBOX = 4
HUMAN_GATE = 2
NO_MEANINGFUL_DELTA = 6
WAITING_UPSTREAM_CHANGE = 0
NOT_WORTH_ACTIVATING = 0
SECOND_PILOT = NO
GENERIC_EXECUTABLE_TOOL_WORKER = NOT_ENABLED
D_MONEY = NOT_ACCESSED_BY_THIS_TASK
PUSH = NO
```

验证：全量测试 `171 PASS`（含 USED 后避免重复绑定、实现身份限定的回归测试）；Python 编译、JavaScript 语法和 `git diff --check` 通过。仅本地提交，不移动 `v0.1.0` tag，不推送 GitHub。
