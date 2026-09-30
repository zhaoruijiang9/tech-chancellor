# 技术丞相 · TechChancellor

**知道你的 AI 已经会什么、还缺什么，帮助它安全地发现、验证、激活和复用新能力。**

技术丞相是本地能力控制中心，不只是 GitHub 收藏夹，也不是自动安装器。它分别记录“已经评审”“现在可用”“确实用过”，让能力积累有证据、可追踪。

[English](README.md) · [使用文档](docs/USAGE.md) · [v0.2.0 发布说明](docs/releases/v0.2.0.md)

![技术丞相控制中心：独立空白安装](docs/images/control-center.jpg)

## 核心闭环

**发现 → 理解 → 验证 → 激活 → 复用 → 持续刷新**

Radar 找到公开技术来源，Chancellor 判断它是否补充现有能力。受支持的低风险实现经验证后成为 AVAILABLE；正式消费者的真实使用证据使它成为 USED。能力发现的新候选继续回到同一条最终评审主链，可以验证，也可以观察或拒绝。

**来源不等于实现，实现不等于能力。** 一个仓库可以提供多项能力，多种实现也可以提供相同能力。收藏项目不是“拥有能力”的证明。

## 五分钟开始（Windows）

需要 Python 3.11+ 和 Git。运行依赖仅为 Python 标准库；Codex、GitHub 登录和计划任务不是基础启动要求。

```powershell
git clone https://github.com/zhaoruijiang9/tech-chancellor.git
cd tech-chancellor
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe run.py init
.venv\Scripts\python.exe run.py health
.venv\Scripts\python.exe run.py dashboard --browser
```

也可双击 `打开技术丞相.cmd`，默认打开桌面式本地窗口。`init` 可重复执行，不覆盖已有本地选择，不安装能力或计划任务。新用户从空个人状态开始，不继承作者的评审、能力或授权记录。

在另一终端开始一次有界、只读的公开发现：

```powershell
.venv\Scripts\python.exe run.py scan --config config/discovery.quickstart.json --dry-run
.venv\Scripts\python.exe run.py build-library
.venv\Scripts\python.exe run.py my-capabilities
```

匿名 API 可能限流，系统会明确报告降级；基础页面仍可用。这一步不会调用 Codex、安装项目或执行第三方代码。

## 真实案例

[awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills) 的只读索引经过版本固定、检疫、静态审查、回滚演练、功能测试和评估，成为可用的 Skill 生态发现能力。随后 Radar 的真实生产调用提供了 USED 证据。

它发现 [context-engineering-kit](https://github.com/NeoLabHQ/context-engineering-kit)，经有界 README 取证、统一候选准入，进入正式 Chancellor。实际最终判断是 **REFERENCE_ONLY（仅作参考）**：重叠较高，暂无已证明的增量收益，因此没有安装、没有执行。

技术丞相不仅判断“装什么”，也判断“不值得装什么”。案例不会作为个人状态注入新用户安装。

## 安全边界

**SAFE_BY_CONTAINMENT**：自动路径只允许低风险、有界、可回滚、已有安全适配器支持的行为。初步语义筛选不是最终 Chancellor 决策。

v0.2.0 **不会自动执行任意第三方 Python、Node、CLI 或 MCP 服务**。安全第三方执行沙箱仍是平台缺口；凭据、服务、权限、金融账户及受保护项目保留人工边界。

数据库、用户批准、安装版本、active pointer、使用回执、缓存和个人报告仅保留本地。`CONFIG != STATE`：通用说明不代表任何人已经拥有或批准采用该能力。

## 可选配置

- Codex CLI：正式 Stage B 和上游语义复审需要它；基础页面不需要。模型优先级为环境变量 → 本地忽略配置 → CLI 默认，不绑定作者的模型名。
- GitHub 认证：可用进程环境变量提高公开 API 额度，不要把 token 写入仓库。
- Windows 计划任务：明确、可撤销的可选部署，初始化不会创建。
- Obsidian：可选 Markdown 阅读器，控制中心自身也能阅读文档。

[详细配置、调度、维护命令和升级](docs/USAGE.md)

## 从 v0.1.0 升级

先停止自己的后台运行，将 `state/`、本地配置和安装目录备份到 checkout 外，再更新代码并运行 `python run.py init`。迁移是幂等的，保留有效历史记录，不需要删除数据库。Git 更新可能移除旧版本曾跟踪的个人文件，升级前的外部备份不可省略。

## 反馈与交流

欢迎反馈有用或噪声推荐、能力方向、安装体验以及过于保守或激进的激活边界。

- [Bug / 功能建议：GitHub Issues](https://github.com/zhaoruijiang9/tech-chancellor/issues)
- [公开讨论：GitHub Discussions](https://github.com/zhaoruijiang9/tech-chancellor/discussions)
- 私下联系：**2565455406@qq.com**

[Apache-2.0](LICENSE)。这是早期开发者工具，不声称企业级完备或盈利能力。[更新记录](CHANGELOG.md) · [贡献说明](CONTRIBUTING.md) · [文档索引](docs/README.md)
