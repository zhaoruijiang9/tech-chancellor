# TechChancellor pre-publication and protected-access audit v0.5

审计日期：2026-09-09

## 产品与品牌

- `PRODUCT_NAME = TechChancellor`
- `CHINESE_NAME = 技术丞相`
- `LOCAL_PROJECT_PATH = D:\personal-tech-intelligence`
- `RECOMMENDED_GITHUB_REPOSITORY = tech-chancellor`
- `INTERNAL_PTI_RENAME = NOT_PERFORMED`
- 内部 Python 模块、数据库表、历史任务和本地目录保持 PTI 原名，避免无意义迁移。

## 受保护项目访问

- `PROTECTED_PROJECT_POLICY = DEFAULT_DENY`
- `TASK_SCOPED_READONLY_AUTH = IMPLEMENTED_AND_TESTED`
- 授权必须同时匹配能力、目标路径、只读模式、架构分析目的、外部输出边界、当前任务标识、未过期时间和 nonce。
- 缺失授权、错误路径、写权限、过期授权、短 nonce、目标内输出均拒绝。
- `D:\money READ = NOT_PERFORMED`
- `D:\money WRITE = NO`
- `D:\money MODIFIED = NOT_VERIFIED_IN_THIS_RUN`
- 当前受控 Archify wrapper 仍未执行受保护项目读取；未生成 Money 架构快照或图。

## 公开准备度

- `GITHUB_PRIVATE_READINESS = CONDITIONAL`
- `PUBLIC_V0_1_READINESS = NOT_YET`
- `README_STATUS = PASS_WITH_LIMITATIONS`：已补充 TechChancellor 品牌、中文 README、核心链路、安全边界和可执行基础命令。
- `PATH_AUDIT = IMPROVED`：PowerShell/批处理计划任务从脚本目录推导项目根，Codex 默认路径从用户主目录解析。
- `RUNTIME_STATE_HYGIENE = PASS_FOR_NEW_RUNTIME_STATE`：state、日志、缓存、quarantine、工作目录和用户产物已加入忽略规则；历史已跟踪个人产物仍保留作证据。
- `THIRD_PARTY_AUDIT = CONDITIONAL`：Archify 固定版本、wrapper、manifest、许可证和收据在仓库中；完整第三方依赖树未作为产品源码发布。
- `SECRET_AUDIT = NO_CURRENT_TREE_VALUE_FOUND`：本轮只检查敏感关键词和跟踪范围，未输出任何疑似秘密值；未执行历史重写。
- `PERSONAL_DATA_AUDIT = CONDITIONAL`：历史报告仍含本机路径和内部运行叙述，适合私有仓库；公开前需单独决定历史报告清理范围。
- `LICENSE_STATUS = DECISION_REQUIRED`：当前没有项目 LICENSE。建议在公开发布前由项目所有者选择 MIT 或 Apache-2.0。
- `CLEAN_INSTALL_SMOKE = NOT_RUN`：当前工作区已有用户运行状态和受控能力，尚未建立隔离 clone 做完整安装烟测。
- `HISTORY_INTEGRITY = NOT_FULLY_AUDITED`：未重写历史；公开前仍需对主要历史提交做逐提交可运行性审计。

## 验证证据

- 单元测试：`72/72 PASS`
- Python 编译检查：`PASS`
- CLI 健康检查：`DEGRADED_HISTORY_ONLY`，两个正式任务 Ready、无 pending；遗留问题为历史重复记录。
- PTI 中文架构图：上一轮三张均 Archify `9/9`，用户入口为 `D:\项目架构图\总目录.html`。
- PTI 本地 Git 未推送；本轮禁止创建 remote、push、release。

## 当前真正阻塞项

1. `D:\money` 架构交付：受控 Archify skill/wrapper 仍明确禁止访问该路径，本轮没有绕过，因此未生成。
2. `LICENSE_DECISION_REQUIRED`：公开发布前必须由用户选择许可证。
3. `CLEAN_INSTALL_SMOKE_NOT_RUN`：需要隔离目录和可用本地 Git clone/archive 条件后再执行。
4. 历史报告可能包含私人路径：公开前需要单独审查，不自动重写历史。

## 最终状态

- `TASK_STATUS = PARTIAL_WITH_HARD_BOUNDARY`
- `RUNTIME_STATUS = HEALTHY_WITH_PRESERVED_LEGACY_WARNING`
- `PROTECTED_PROJECT_ACCESS_STATUS = TASK_SCOPED_POLICY_IMPLEMENTED`
- `MONEY_ARCHITECTURE_STATUS = BLOCKED_BY_CONTROLLED_ARCHIFY_BOUNDARY`
- `MONEY_INTEGRITY_STATUS = NO_WRITE_OR_EXECUTION_PERFORMED`
- `NEXT_MODE = PRIVATE_READINESS_REVIEW_AFTER_BOUNDARY_DECISION`
