# TechChancellor Capability Intelligence V1

日期：2026-09-29。范围仅为 `D:\personal-tech-intelligence`；没有读取受保护的交易项目，没有安装或升级第三方项目，也没有推送远端。

## 结论与对象边界

`SOURCE` 是 GitHub 等来源，`IMPLEMENTATION` 是来源提供的工具或工作流，`CAPABILITY` 是用户要获得的能力，`METHOD` 是可被实际工作流采用的做法，`EVIDENCE` 记录可核验机制和使用，`PERSONAL STATE` 记录个人当前状态。一个来源可映射多项能力，多种实现也可提供同一能力。候选能力定义不代表已拥有。`implementation_capabilities.delta_kind` 只表达有证据支撑的新增、重叠、替代、补充或无显著增量；star 数不参与该判断。关系表目前仅有 3 条有说明的关系，不为凑齐关系类型制造边。

原 14 条已评审仓库保留为 14 个来源、14 个候选实现，映射到 12 种去重后的能力定义：项目架构可视化、规格驱动开发、可追踪实施门槛、结构化开发工作流、仓库上下文映射、代码库语义检索、Agent 工作流编排、上下文压缩、桌面上下文采集、Skill 生态发现、多 Agent 金融研究、量化回测实验。它们不是“14 个已安装能力”。唯一已通过隔离验证和真实使用证据进入个人能力栈的是 `PROJECT_ARCHITECTURE_VISUALIZATION`，实现为已固定版本的 Archify；当前个人状态为 AVAILABLE、VERIFIED、USED。原 89 条判断历史、用户反馈和激活证据没有重写或删除。

迁移在独立 SQLite 表中保存新模型，标记 `reviewed_sources_v1` 防止重复映射覆盖后续人工状态。迁移前备份位于忽略目录 `state/backups/intelligence-before-capability-v1-20260929-101156.db`，原库与备份均通过完整性检查。空库可以初始化并展示空 Dashboard，不依赖这 14 条历史数据。

## 方法真实性

BMAD 与 Spec Kit 各提取 3 条方法候选，共 6 条 `METHOD` 记录；它们的现有证据都是来源阅读/提炼，未发现可归因的本地 workflow mechanism 加 verified use 组合，因此 `ADOPTED_METHODS=0`。类似“先规划、再验证”的普通做法不能在没有出处和使用证据时算作采纳了 BMAD 或 Spec Kit。方法进入“已采纳”必须同时有明确工作流落地机制与真实使用记录；本轮没有为了保留旧数字而伪造证据。

对 [BMAD 当前仓库](https://github.com/bmad-code-org/BMAD-METHOD) 与 [v6.12.0 发行说明](https://github.com/bmad-code-org/BMAD-METHOD/releases/tag/v6.12.0) 的复核发现：上游当前 README 提供 Codex plugin/skill 路径，发行版强调按任务规模选择流程、简短规格和带证据的评审裁决。这使它值得继续作为结构化交付方法来源，但本地没有可核验的 BMAD 安装、专属调用机制或真实使用；当前结论是 KNOWLEDGE_REFERENCE / WATCHLIST，不自动全局安装。仓库当前主线内容可能晚于该发行版，不能把主线文档全部归到 v6.12.0。

对 [Spec Kit Codex 集成说明](https://github.com/github/spec-kit/blob/main/docs/reference/integrations.md) 与 [v1.0.12 发行说明](https://github.com/github/spec-kit/releases/tag/v1.0.12) 的复核发现：上游支持通过 `.agents/skills` 对接 Codex，但本地未见 Spec Kit 特有技能、项目宪章或可归因使用记录。规格先行、验收门槛与可追踪规划目前仅是参考方法，不是已采纳方法。

## 候选与人工边界

Archon 保持 `VALIDATION_FAILED`。官方 [v0.11.0 说明](https://github.com/coleam00/Archon/releases/tag/v0.11.0) 包含 Windows 工作区识别、失败 worktree 清理与锁定、凭据脱敏等相关修复；[v0.11.1](https://github.com/coleam00/Archon/releases/tag/v0.11.1) 是后续补丁。这些是值得定向重审和重新做隔离验证的上游**声明**，不是本机的 rollback、凭据边界或执行隔离已通过证明。本轮没有安装或重新激活。首次指纹之前的历史版本未知，因此本轮当前状态审查没有伪装成自动 `delta_review` 完成记录。

backtesting-engine 的 `APPROVE_FOR_REVIEW` 反馈保留，准确状态为 `APPROVED_WAITING_VALIDATION`：已批准继续隔离评估，尚无正在执行的验证任务，也未部署或连接 broker。TradingAgents 仍是唯一未解决的 owner decision，不自动替用户决定；MetaGPT、LangChain 仍不采用。其余 8 个实现处于 WATCHLIST，其中 BMAD、Spec Kit 仅作为方法来源和知识参考。

## 持续更新机制

沿用现有 Windows Radar 计划任务，扫描后隐藏启动独立的上游检查脚本；其失败写入独立日志和健康提醒，不阻断 Radar 或 Chancellor。脚本通过既有 `gh auth` 在子进程内传递令牌，不记录令牌。检查周期从上次检查时间计算：USED 3 天，方法来源/等待验证/人工决策 7 天，WATCHLIST 14 天，不采用/验证失败 30 天，归档 90 天。定时入口自身无需 Codex 常驻；仅有待复审队列时才尝试 Codex 增量复审。

Stage 1 用有请求预算的 GitHub API 获取仓库元数据，必要时再取 HEAD、最新 release、特定来源 README SHA；不会批量 clone 或每次全量 AI 重审。首次建立指纹标记 `BASELINE_CAPTURED`，评审新鲜度保留 `UNKNOWN`，因为历史评审对应的精确上游提交无法追认。后续无变化为 `NO_CHANGE`；release 变化、方法来源相关变化，或可能触及验证失败原因的更新才进入去重的 Stage 2 队列。普通 HEAD typo 不触发深审，旧版发行说明的关键词不能冒充本次修复。网络失败、配额失败、系统失败分别记录，不覆盖旧指纹，也不误判为无更新。

Stage 2 只读旧判断、当前个人状态、旧/新版本和有限的 compare 元数据，给出 `NO_RELEVANT_CHANGE`、`REVIEW_STILL_VALID`、`REVIEW_UPDATED`、`REVALIDATION_REQUIRED`、`OWNER_DECISION_MAY_CHANGE` 之一，并保存证据。证据不足或调用失败保持 PENDING 与 STALE，最多自动重试 3 次后显示人工注意；上游变化不能自动改变个人状态、激活记录、固定版本或原判断。**AUTO_UPGRADE=NO**，也没有自动 install、pull、pip/npm update 或交易系统接入。

## 真实验证与当前数字

正式库迁移后：14 条来源、14 个候选实现、12 种能力定义、6 条参考方法、3 条能力关系，原 89 条判断历史仍在。14 个来源首次真实检查得到 14 个 `BASELINE_CAPTURED`（45 次 API 请求、0 失败）；再次强制检查得到 14 个 `NO_CHANGE`（16 次请求、0 失败）；日常定时入口按周期跳过未到期来源（0 次请求），复审入口返回 `NO_PENDING`。模拟上游变更的测试覆盖 `CHANGE -> PENDING -> DELTA REVIEW -> CURRENT`，包括首次网络失败后恢复、失败重试、去重、只读临时 Codex 调用、保留旧决定和不自动升级；正式环境没有待审变更，因此未声称生产 Codex 复审已有真实变化样例。Dashboard 的 summary、capabilities、activity 接口均完成本地 HTTP smoke。全量测试为 140 PASS。

| 指标 | 实际值 |
| --- | ---: |
| REVIEWED_SOURCES | 14 |
| CAPABILITIES（定义，非全部已拥有） | 12 |
| IMPLEMENTATIONS（候选，非全部已安装） | 14 |
| ADOPTED_METHODS | 0 |
| USED_CAPABILITIES | 1 |
| AVAILABLE_CAPABILITIES | 1 |
| WAITING_VALIDATION | 1 |
| ACTIVELY_VALIDATING | 0 |
| HUMAN_DECISIONS | 1 |
| WATCHLIST | 8 |
| STALE_REVIEWS | 0 |
| UPSTREAM_CHANGES_PENDING_REVIEW | 0 |

以上统计来自 2026-09-29 本地正式库快照。Archify 的 AVAILABLE 与 USED 是同一个能力，不可相加成两个。14 个来源的 `REVIEW_FRESHNESS=UNKNOWN` 表示没有历史版本锚点；它不同于已检测到更新而尚未复审的 STALE。
