# 技术丞相（TechChancellor）

这是一个面向 AI 辅助开发的个人技术情报与能力激活系统。

它自动发现与你有关的新技术，判断是否真正增加你的能力，在安全边界内验证和激活，并让 Codex 在未来项目中直接复用。项目内部历史名称是 PTI（Personal Tech Intelligence）。

需要 Python 3.11+ 和 Git。项目运行时只使用 Python 标准库，不要求联网安装第三方包。进入项目根目录后，先初始化本地运行目录和 SQLite 数据库：

```powershell
$env:PYTHONPATH = "$PWD\src"
python run.py init
python run.py health
python run.py scan --dry-run
python run.py build-library
python run.py my-capabilities
```

`init` 是幂等操作，可以安全重复运行。也可以先用 `python -m venv .venv` 创建隔离环境，再使用 `.venv\Scripts\python.exe` 执行上述命令。网络扫描是公开 GitHub 数据的手动 dry-run；Codex 语义审查和 Windows 计划任务都是可选配置，不会在初始化时偷偷启用。

系统默认不安装、执行或连接第三方项目，不连接交易账户，也不自动下单。运行 `python run.py my-capabilities` 后会生成本机能力清单；该文件包含本机状态，不应提交到公共仓库。完整说明见 `README.md`。

## 反馈与交流

如果你正在使用 TechChancellor，欢迎反馈 bug、使用体验、能力推荐或产品设计建议。

- Bug / 功能建议：GitHub Issues
- 公开讨论：Public release 后启用 GitHub Discussions
- 私下联系：`2565455406@qq.com`

特别欢迎反馈哪些技术发现真正有用、哪些推荐是噪声、哪些 capability 值得自动激活、激活边界是否过于保守或激进、新用户安装是否困难、Codex 检索是否节省搜索时间，以及 Windows/Codex 环境兼容性问题。
