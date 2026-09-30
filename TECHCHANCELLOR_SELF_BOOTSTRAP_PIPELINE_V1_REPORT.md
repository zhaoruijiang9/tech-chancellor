# TechChancellor Self-Bootstrap Candidate Pipeline V1

日期：2026-09-30。起始代码基线：`7520b4af541dcf7a5d7ea7020e0272f7b4780039`。

## 结论与根因

`SELF_BOOTSTRAP_LOOP = PASS`。已有 USED 索引能力发现的真实候选已回到共享正式 Stage B，产生真实 Codex Chancellor 决策并持久化到对应下游状态。PASS 不意味着这个候选值得安装，更不意味着它成为第三个 USED 能力。

原生和 capability 来源原先已经在 `discovery.run_discovery` 中按 GitHub repository ID 合并、评分和本地取证；并不存在另一套 capability Stage B。真正断点是 `cli.run_once` 把 `build_report` 的展示子集传给 `write_chancellor_pending`。`build_report.high_priority` 只保留前 5 项：context-engineering-kit 得分 36，完成本地初筛，却被展示前列排除，因而没有评审包。旧库仅保留观测的取证等级和计数，没有保存这次 README/本地评审内容，进一步造成无法直接恢复。

之前的“公平位”确实是 source-specific：候选截断会替换为 capability 新来源，取证也优先它。现在改为通用来源多样性：最多调整 1 位，至少 2 个名额才生效，第一名不被替换；补位对象必须高质量、意图相关、非高风险。最终交接前仍统一核对身份、意图、README、评分、去重及评审到期规则，来源不授予信任或部署权限。

## 共享业务链

- `canonical_candidates` 保存有界证据、初筛结果、准入、来源、评审指纹和阶段；`candidate_pipeline_events` 保存幂等审计事件。
- 展示仍是原来的前 5/次要 10 项，正式交接读取完整合格结果及已保存待交接候选，不再由页面截断决定业务命运。
- 所有来源复用 `write_chancellor_pending` / `build_stage_b_packet` / `run_stage_b`。包中包括仓库身份、provenance、最多 6000 字符 README、最多 100 条路径、初筛、能力假设、重叠线索、已有关系、当前能力背景及风险。
- 同一身份只保留一个活动待评审包；重复扫描复用包，多来源合并 provenance。已有最终决定不重复交接；实质变化、人工请求或到期观察的合法复评仍可新建一个评审周期。
- Stage B 后创建/更新 Source 与 Implementation；已知能力映射仍标记为未验证假设，不虚构 OWNED、AVAILABLE 或 USED。没有匹配假设时允许空映射，保留 source/implementation 的真实终态。
- WATCH/REFERENCE 无执行队列；IGNORE/ARCHIVE/NO_MEANINGFUL_DELTA 不激活；人工门槛优先于适配器选择。已有只读索引适配器可复用当前 activation queue/worker；没有安全执行路径则记录 OS sandbox 阻断。未重写 Activation Engine。
- 本地 `LocalSemanticChancellor` 是证据规则和排序参考，不是最终 LLM 决策。看板与调用动态采用“初步语义筛选”与“最终 Chancellor 评审”两种明确措辞。
- SQLite 的无时区 UTC 时间在读取层补为 UTC ISO 格式，避免最终决定与新流水线事件显示相差 8 小时或排序错误；未改写历史时间。
- 超过 24 小时已合格初筛却没有包/最终决定的候选触发 `PIPELINE_STALLED` 健康项；未增加高频告警或计划任务。

## 真实恢复与最终决定

```text
REAL_CANDIDATE = NeoLabHQ/context-engineering-kit
GITHUB_REPOSITORY_ID = 1096085345
DISCOVERY_SOURCE = SKILL_ECOSYSTEM_DISCOVERY
SOURCE_IMPLEMENTATION = impl:ComposioHQ/awesome-claude-skills
CONSUMER = RADAR_DISCOVERY
ORIGINAL_SCAN_ID = 133be1cc150b
CANONICAL_ADMISSION = PASS
STAGE_B_PACKET = 1096085345--f43d465d6bcbb0b6.json
STAGE_B_RUN = d5d71ee5bd2f
STAGE_B_MODEL = gpt-5.6-sol
STAGE_B_DECISION = REFERENCE_ONLY
DOWNSTREAM = SOURCE + IMPLEMENTATION(REFERENCE_ONLY) + TIER_0_KNOWLEDGE_PATTERN
DUPLICATE_PACKET = NO
ACTIVATION_STARTED = NO (no executable queue job, no third-party code execution)
OBSERVATIONS_BEFORE = 3
OBSERVATIONS_AFTER = 3
EXECUTABLE_ACTIVATION_JOBS = 0
SELF_BOOTSTRAP_LOOP = PASS
```

最终 Chancellor 原文要点：可作为提示词、规则、provider adapter、SDD 文档的参考资料，但与现有规划、调试、TDD、审查、子任务和验证流程高度重叠；没有比较测试证明新增能力或改进。整包安装还可能带来指令冲突、额外上下文与兼容/许可证审查成本。因此仅作参考，不进行执行型激活。`ACTIVE_PATTERN` 只是已有 TIER_0 的知识参考投影，不是安装、运行或 USED 证明。

先执行单候选 dry-run，发现历史 README 未持久化；应用恢复时未新增观测。首次证据刷新遇到公开 GitHub API 403 限流，保留准入失败；随后仅在进程内使用已登录 GitHub CLI 的凭据读取公开证据，未输出/保存 token。每次刷新预算 4 个请求、README 6000 字符；刷新内容明确标记为当前证据，而非伪造历史 README。修复前已进行 SQLite 在线备份：`state/backups/self-bootstrap-before.db`（本机运行数据，不入 Git）。

前两次 Stage B 调用真实失败：全局 Codex 配置的 `gpt-6.1-sol` 被当前 ChatGPT CLI 服务拒绝。已为本项目设置独立 `config/stage_b.json`，使用本机 CLI 返回的可用列表中的 `gpt-5.6-sol`，不修改全局配置。第三次仍走原来的只读、ephemeral、schema-constrained Codex CLI 路径，真实返回并持久化 `REFERENCE_ONLY`，没有 mock 或本地规则冒充最终判断。

再次恢复返回 `ALREADY_DECIDED`；只有一个对应 processed packet。原 `SKILL_ECOSYSTEM_DISCOVERY` 的 VERIFIED / AVAILABLE / USED 及真实使用证据保持不变；发现能力的 material use 不依赖下游必须采用。

## 剩余记录与边界

同类历史 evidence-ready、无包无最终决定记录还剩 **1** 条：`emaynard/claude-family-history-research-skill`。这是待逐项重核准入的统计，不是合格候选数量；上一轮已经记录它与量化研究意图不符。本轮没有恢复它，也没有全历史 backfill。

既有 Fission-AI/OpenSpec、ruvnet/ruflo 两个活动 pending 未由本轮处理。总健康状态仍为 `NOT_EVALUATED`，原因是这些既有 pending 和计划任务上次非零结果；新 canonical pipeline 没有 `PIPELINE_STALLED`，没有陈旧锁。一次目标 E2E 的 PASS 不能冒充整个后台所有积压已健康。

```text
NEXT_PLATFORM_BLOCKER = SECURE_THIRD_PARTY_EXECUTION_SANDBOX
PLATFORM_STATE = MISSING_CAPABILITY (preserved)
OS_SANDBOX_IMPLEMENTED = NO
NEW_DISCOVERY_SOURCE = NO
NEW_PILOT = NO
NEW_USED_CAPABILITY = NO
D_MONEY = NOT_ACCESSED
VISUAL_BASELINE = USER_ACCEPTED_UNCHANGED
PUSH = NO
V0_1_0_TAG = 5c79e04dcd2c414f11bf3797af49040a9ca5aa16 (unchanged)
```

## 验证与操作入口

`190 tests PASS`，其中新增 19 项覆盖共享准入、展示截断、同身份多来源、README 上限、幂等、合法复评、来源无单名额特权、意图/证据/质量拒绝、恢复、停滞检查、真实 Stage B 路径的测试桩集成、下游投影、WATCH/no delta 不排队、安全适配器排队、凭证人工门槛及看板交互状态。测试桩仅用于测试；上述真实 E2E 无 mock。

Python compileall、前端 `node --check`、`git diff --check` 通过。真实 Dashboard 详情页已检查来源、初筛和最终决定；已安装与可运行均显示“否”。本地入口：`http://127.0.0.1:8766/`。

```powershell
python run.py repair-stranded-candidates OWNER/REPO
# Inspect the dry-run result before applying one repository only.
python run.py repair-stranded-candidates OWNER/REPO --apply
python run.py stage-b OWNER/REPO --limit 1
python run.py health
```

Git 仅提交本轮代码、测试、项目配置、README 和本报告；运行库、备份、packet、raw decision、生成投影仍被忽略。提交 SHA 由包含本报告的最终逻辑提交确定，见 `git log -1`，避免把自引用 SHA 写入该提交内容。未 push，未移动 release tag。
