# PERSONAL_TECH_INTELLIGENCE_PHASE_1_MVP_REPORT

- 日期：2026-08-26（Asia/Shanghai）
- 范围：Phase 1，手动、只读、无第三方代码执行
- 最终判断：`PARTIAL_PASS`
- 结论：搜索型 MVP 已通过；完整 GitHub 元数据增强仍受未认证 core 配额限制。

## 1. PHASE_0_SCOPE_AMENDMENTS

- 新增正式领域：`AI_EXPERIENCE`。
- `AI_AGENT` 保留为 Agent framework、MCP、Skill、编排和运行时基础设施。
- `AI_EXPERIENCE` 专门关注上下文连续性、记忆、搜索、Token/上下文成本、工具发现、项目理解、调试、观测和评估。
- 保留 `Python modular monolith + SQLite + local file inbox + structured Chancellor review`。
- Phase 1 没有 quarantine、clone、安装、执行、部署或调度注册。

## 2. AI_EXPERIENCE_DOMAIN

已加入策略域、路由域和本机能力画像。评分关注：减少重复上下文、改善长项目连续性、提高搜索和旧信息定位质量、降低 Token 成本、减少复制粘贴、改善 Skill/MCP 发现、提升 coding-agent 成功率，以及提高调试和评估可观察性。

当前查询组启用了一个有限的 `context engineering AI language:python` 查询。完整语义范围已在策略层保留，未被固定关键词锁死。

## 3. GITHUB_REST_PREFLIGHT

使用当前 Python 环境和官方 `https://api.github.com`，没有 `gh`、token 或连接器登录。

实测结果：

- HTTPS：`PASS`
- repository search：`PASS`，HTTP 200
- 稳定 repository ID：`PASS`，示例 `909213664`
- owner/repo、canonical URL、description：`PASS`
- topics、stars、forks、created_at、updated_at、pushed_at：`PASS`
- default branch、license、fork：`PASS`
- 分页：`PASS`
- `/rate_limit`：`PASS`
- repository detail：`BLOCKED_BY_CURRENT_CORE_RATE_LIMIT`
- latest release：`BLOCKED_BY_CURRENT_CORE_RATE_LIMIT`
- latest commit：`BLOCKED_BY_CURRENT_CORE_RATE_LIMIT`
- parent relation：接口路径已设计，但本次详情请求未能取得 200，因此状态为 `UNVERIFIED`

示例搜索结果为 `TauricResearch/TradingAgents`，其公开搜索结果包含 repository ID、Apache-2.0、topics、stars/forks 和时间字段。该示例只证明 API 返回结构，不代表项目获得推荐。

## 4. RATE_LIMIT_EVIDENCE

预检保持低请求量，共 6 个请求，随后补做 1 个单独搜索字段确认请求。

- search header 曾返回 `X-RateLimit-Limit: 10` 和 `X-RateLimit-Remaining: 5`，分页请求曾返回 remaining 4。
- 单独字段确认搜索返回 HTTP 200，remaining 9。
- `/rate_limit` 返回 core `limit=60, remaining=0, used=60`，search 资源显示可用额度。
- 仓库详情、release、commit 的 403 与 core 资源耗尽一致，系统将其记录为部分 API 失败，不转译为“没有候选”。
- Phase 1 只依赖 search，因此未认证搜索足以支撑当前小规模 MVP；详情增强暂不进入成功判定。

## 5. SOURCE_CONTRACT

Phase 1 的主入口是公开 GitHub repository search，使用固定 User-Agent、官方 JSON Accept header、每次请求超时和请求预算。

客户端保留 search、repository detail、latest release、latest commit 的独立结果；403、超时、预算耗尽和解析错误都产生结构化失败。搜索成功但详情失败时，候选仍可进入“部分元数据评审”，但不得伪装为完整来源验证。

没有使用仓库提供的 URL 进行跟随请求，没有读取账号、token 或本机凭据。

## 6. LOCAL_CAPABILITY_PROFILE

已创建 `config/local_capability_profile.json`，只记录已验证能力和明确的 `UNKNOWN`：

- AI coding agent：Codex skills、插件/MCP 能力和既有 AI agent 项目存在，精确重叠为 `UNKNOWN`。
- AI experience：Codex task、文件、Web、截图、记忆指导和自动化存在，semantic search 覆盖为 `UNKNOWN`。
- Quant data：`D:\money` 与 TDX 只读能力存在，外部研究覆盖为 `UNKNOWN`。
- Productivity：Python、Node、SQLite、uv、Git 和本地自动化存在。
- Research：Jupyter Notebook skill 存在。
- GitHub 连接：`UNKNOWN`，因为插件账号未连接。
- Local LLM：本机存在 AI 工具和模型目录，精确可运行清单为 `UNKNOWN`。

没有扫描密码、token、账号快照或敏感用户内容。

## 7. IMPLEMENTED_ARCHITECTURE

已实现独立根目录 `D:\personal-tech-intelligence`，包含：

- `src/pti/models.py`：稳定数据模型。
- `src/pti/storage.py`：SQLite 初始化、幂等 upsert 和评审历史回写。
- `src/pti/github_api.py`：官方 REST 搜索和部分失败封装。
- `src/pti/discovery.py`：有限 query groups、候选上限、去重和评审接线。
- `src/pti/policy.py`：评分、Capability Delta、AI_EXPERIENCE 路由和硬门禁。
- `src/pti/chancellor.py`：结构化丞相评审入口。
- `src/pti/reporting.py`：JSON/Markdown inbox 和报告，含领域多样性与跨运行唯一文件名。
- `src/pti/cli.py`、`run.py`：手动 dry-run 和输出根目录保护。

实现只使用 Python 标准库，没有引入第三方依赖。

## 8. SQLITE_SCHEMA

SQLite 文件为 `state/intelligence.db`，核心表 `repositories` 以 `github_repository_id` 为主键，包含：

`canonical_owner_repo`、`url`、`first_seen`、`last_seen`、`stars`、`forks`、`pushed_at`、`release_state`、`license_spdx`、`is_fork`、`parent_repository_id`、`previous_score`、`previous_decision`、`previous_routes`、`rejection_reason`、`review_after`、`content_fingerprint`、`description`、`topics` 和 `default_branch`。

已验证重复 upsert 不新增记录，仓库改名仍保持单一稳定身份；评审结果会回写历史字段，支持后续冷却和去重。

## 9. DISCOVERY_LANES

当前配置为有限查询组：

- `AI_AGENT`：Agent framework、MCP tools。
- `AI_EXPERIENCE`：context engineering。
- `QUANT_DATA`：quant research data。
- `PRODUCTIVITY`：AI productivity automation，作为可配置后续组。

策略层同时支持 `BUSINESS_MONEY`、`RESEARCH_LEARNING`、`WATCHLIST` 和 `CHANGE_SIGNAL`，但本次只启用少量查询以控制 API 配额和信息噪声。`MONEY_TRADING` 仅作为受控 route，不作为宽泛交易机器人搜索词。

配置支持 per-query cap、total candidate cap、request budget、cooldown、lookback 和报告上限。

## 10. SCORING_AND_CAPABILITY_DELTA

保留 Phase 0 评分维度：`RELEVANCE`、`NOVELTY`、`CURRENT_NEED_MATCH`、`EXPECTED_VALUE`、`MATURITY`、`MAINTENANCE`、`USER_INTEREST`，以及 `INTEGRATION_COST`、`SECURITY_RISK`、`DUPLICATION`。

实现了加权总分和硬覆盖规则：高重复且当前需求低的高星项目可以 `IGNORE`；低星但直接满足当前需求的项目可以 `HIGH_PRIORITY`；高安全风险不会因高分而自动执行。

每个丞相结果包含：

```text
existing_capability
candidate_addition
replacement_potential
incremental_value
```

外部 README/Prompt/Skill 文本只作为 `UNTRUSTED_EXTERNAL_INPUT`，不会改变系统策略。

## 11. CHANCELLOR_SCHEMA

结构化评审输出包含：`decision`、`primary_route`、`secondary_routes`、`score_components`、`score_total`、`priority`、`capability_delta`、`incremental_value`、`evidence`、`risk_flags`、`confidence`、`reason_code`、`review_after` 和 `recommended_next_action`。

Phase 1 允许的决定为：`IGNORE`、`ARCHIVE`、`REFERENCE_ONLY`、`REVIEW_LATER`、`CANDIDATE_FOR_QUARANTINE`、`USER_REVIEW_RECOMMENDED`。本轮没有输出实际下载或执行结果。

## 12. ROUTING_SCHEMA

本地 inbox 支持：

`AI_AGENT`、`AI_EXPERIENCE`、`MONEY_TRADING`、`QUANT_DATA`、`PRODUCTIVITY`、`RESEARCH_LEARNING`、`BUSINESS_MONEY`、`GENERAL`。

每个路由候选输出 JSON 和 Markdown。SQLite 是权威状态；inbox 是稳定消费接口。路由到 `MONEY_TRADING` 只表示“值得独立审查”，不表示交易系统批准采用。

## 13. FILES_CREATED

独立项目文件：

- `src/pti/__init__.py`
- `src/pti/models.py`
- `src/pti/storage.py`
- `src/pti/github_api.py`
- `src/pti/discovery.py`
- `src/pti/policy.py`
- `src/pti/chancellor.py`
- `src/pti/reporting.py`
- `src/pti/cli.py`
- `run.py`
- `config/discovery.json`
- `config/local_capability_profile.json`
- `README.md`
- `tests/test_suite.py`
- `state/intelligence.db`
- `reports/latest.json`、`reports/latest.md`
- `inbox/AI_AGENT/`、`inbox/AI_EXPERIENCE/`、`inbox/QUANT_DATA/`

当前报告为 `PERSONAL_TECH_INTELLIGENCE_PHASE_1_MVP_REPORT.md`。另有实施计划保存在工作区 `docs/superpowers/plans/2026-08-26-personal-tech-intelligence-phase-1.md`。

## 14. TEST_RESULTS

使用 Python 标准库测试运行器：

```text
Ran 15 tests
OK
```

覆盖内容包括：SQLite 幂等与改名、搜索身份解析、403 部分失败、评分对比、AI_EXPERIENCE 路由、提示注入隔离、历史评审回写、报告上限、领域多样性、跨运行 artifact 唯一性和 `D:\money` 输出保护。

由于本机没有 pytest，本轮没有安装它；标准库 unittest 是实际验证工具。

## 15. MANUAL_DRY_RUN_RESULT

运行命令：

```text
python run.py --dry-run
```

结果：

- 运行状态：`PASS`
- 评审候选：20
- GitHub search 请求：4
- API 失败：0
- 报告：5 个 `HIGH_PRIORITY`，0 个 `SECONDARY`
- 实际展示路由：`AI_AGENT`、`AI_EXPERIENCE`、`QUANT_DATA`
- 输出：SQLite、JSON、Markdown，仅写入 `D:\personal-tech-intelligence`
- 运行方式：手动；没有自动任务注册

第二次 dry-run 使用已存在的 SQLite 身份历史，重复项目没有产生重复身份记录。

## 16. SAMPLE_DISCOVERIES

本轮搜索返回的候选包含多个 Agent/量化相关公开项目。示例：

- `TauricResearch/TradingAgents`：搜索返回稳定 ID、Apache-2.0、finance/llm/multiagent/trading topics；进入 `AI_AGENT` 评审，不因 stars 自动批准。
- `langchain-ai/langchain`、`FoundationAgents/MetaGPT`、`microsoft/autogen`、`crewAIInc/crewAI`：作为 Agent 领域候选进入去重和评分链。
- `AI_EXPERIENCE` 和 `QUANT_DATA` 查询也实际产生了独立 route，避免报告被单一 Agent 查询完全占满。

这些是“候选发现”，不是采用建议、交易建议、收益判断或生产授权。

## 17. D_MONEY_INTEGRITY_CHECK

dry-run 前后读取 `git -C D:\money status --porcelain` 并比较 SHA-256：

- `MoneyIntegrity=PASS`
- 前后状态哈希一致：`0F-51-FF-E7-F9-E8-A2-0E-C6-8E-45-51-85-AE-EE-78-61-18-C3-7F-AA-B1-6E-79-B7-D9-16-F2-8E-B3-2B-78`

本轮没有修改 `D:\money`，没有读取券商账户，没有改交易策略、风险、provider、成交或持仓事实。

## 18. KNOWN_LIMITATIONS

- 未认证 GitHub core 额度在预检时为 0，详情、release、commit 不能作为本次成功证据。
- 当前初筛主要依赖搜索返回的公开元数据，不读取 README 内容，因此丞相语义评审仍是轻量版本。
- `PRODUCTIVITY` 等部分查询组受总候选上限影响，当前运行可能提前停止；下一版应增加每域配额或轮询策略。
- 当前没有真正的安全执行沙箱，不支持 Phase 3。
- 没有实现 quarantine 下载、静态依赖扫描、二进制检查或隔离测试。
- 没有注册周期任务，没有向任意 Codex 对话主动发送消息。
- 评分是可解释的 v0.1 规则，不是收益预测器，也不应被用于自动交易决策。

## 19. FIRST_REAL_BLOCKER

Phase 1 搜索 MVP 的原阻断 `GITHUB_DISCOVERY_SOURCE_CONTRACT_NOT_EMPIRICALLY_VALIDATED` 已部分关闭：公开未认证 search、稳定 ID、分页和限流信息均已实测可用，当前不需要 GitHub credential。

仍存在的真实阻断是：

`GITHUB_ENRICHMENT_ENDPOINTS_RATE_LIMIT_UNVERIFIED`

它影响详情、release、commit 和 parent 关系增强，不阻塞当前 search-only MVP。不能把这个部分缺口隐藏成完整 GitHub 来源通过。

## 20. RECOMMENDED_NEXT_TASK

推荐下一任务：`PHASE_1_REVIEW_AND_SOURCE_ENRICHMENT_DECISION`

先人工审阅本报告和示例输出，再决定是否：

1. 保持无 credential 的搜索型 MVP，并加入每域公平配额；
2. 单独设计低权限 GitHub 认证，以稳定取得详情、release 和 commit；
3. 补充 README 静态摘要和内容指纹，但继续不执行第三方代码；
4. 只有 Phase 1 连续几次手动运行稳定后，才讨论 Codex automation；
5. 不进入 quarantine 或隔离测试，直到本机拥有真实安全沙箱并完成独立设计。

当前不建议触碰 `D:\money`、安装第三方 Skill/MCP、注册 Windows 任务、启用自动下载或建设 Agent 集群。
