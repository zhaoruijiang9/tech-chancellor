# TechChancellor

**A personal technical intelligence and capability activation system for AI-assisted development.**

技术丞相（TechChancellor）自动发现、判断、验证并激活与你有关的技术能力，让 Codex 在未来项目中直接复用。它由内部项目名 Personal Tech Intelligence（PTI）演化而来。

## 它解决什么问题

技术变化很快，GitHub 项目很多，star 不等于适合你，Agent 也会重复搜索。真正缺少的是长期能力积累，以及可审计、安全的采用过程。

## 核心链路

`Discover` → `Normalize` → `Review` → `Capability Library` → `Verify` → `Activate` → `Reuse`

- **Radar**：从公开 GitHub 来源发现候选项目。
- **Chancellor**：补充证据并做语义判断。
- **能力库**：保存可检索的能力卡和限制。
- **安全策略**：固定版本、隔离检查、可回滚；敏感能力必须人工批准。
- **用户工具箱**：生成 `MY_CAPABILITIES.md`，供 Codex 在明确任务中复用。

## 快速开始（Windows）

需要 Python 3.11+、Git；网络扫描使用公开 GitHub REST API。项目运行时使用 Python 标准库，不要求第三方包安装。进入项目根目录后，先初始化一次本地运行目录和 SQLite 数据库：

```powershell
$env:PYTHONUTF8 = "1"
$env:PYTHONPATH = "$PWD\src"
python run.py init
python run.py health
python run.py scan --dry-run
python run.py build-library
python run.py my-capabilities
```

如果希望隔离 Python 环境，可先运行 `python -m venv .venv`，再用 `.venv\Scripts\python.exe` 替换上面的 `python`；项目没有需要联网安装的第三方 Python 依赖。首次使用请先运行 `python run.py my-capabilities` 生成本机能力清单，再阅读 `MY_CAPABILITIES.md` 和 `docs/CURRENT_PROJECT_STATE.md`。Windows 计划任务是可选部署步骤，不会由基础命令偷偷创建。

`init` 是幂等操作，可安全重复运行。`scan` 默认是公开 GitHub 数据的手动 dry-run；Codex 语义审查和 Windows 计划任务均为可选的后续配置，不会在初始化时自动启用。

## 安全边界

TechChancellor 采用 **SAFE_BY_CONTAINMENT**：不自动全局安装、不自动连接账户、不自动下单；第三方能力必须固定版本并经过隔离/静态检查。受保护项目默认拒绝访问，只有当前任务提供路径、目的和只读范围明确的授权时，受控 wrapper 才可读取架构信息，输出必须在目标项目之外。

## 发布状态

当前为 `v0.x` 预发布版本。私有 GitHub 准备度见 `TECHCHANCELLOR_PRE_PUBLICATION_AND_PROTECTED_ACCESS_V0_5_REPORT.md`。未来公开仓库建议名称：`tech-chancellor`。本仓库不包含用户个人运行数据库、日志、交易数据或 `D:\项目架构图` 产物。

## Feedback and Contact

If you use TechChancellor, feedback on bugs, user experience, capability recommendations, and product design is welcome.

- Bugs and feature ideas: GitHub Issues
- Public discussion: the GitHub Discussions channel will be enabled with the public release.
- Private contact: `2565455406@qq.com`

Useful feedback includes which discoveries are valuable or noisy, which capabilities deserve activation, whether activation boundaries are too conservative or aggressive, installation difficulties, Codex retrieval usefulness, and Windows/Codex compatibility issues.
