# 技术丞相（TechChancellor）

这是一个面向 AI 辅助开发的个人技术情报与能力激活系统。

它自动发现与你有关的新技术，判断是否真正增加你的能力，在安全边界内验证和激活，并让 Codex 在未来项目中直接复用。项目内部历史名称是 PTI（Personal Tech Intelligence）。

先运行：

```powershell
$env:PYTHONPATH = "$PWD\src"
python run.py health
python run.py scan --dry-run
python run.py build-library
python run.py my-capabilities
```

系统默认不安装、执行或连接第三方项目，不连接交易账户，也不自动下单。完整说明见 `README.md`。

## 反馈与交流

如果你正在使用 TechChancellor，欢迎反馈 bug、使用体验、能力推荐或产品设计建议。

- Bug / 功能建议：GitHub Issues
- 公开讨论：Public release 后启用 GitHub Discussions
- 私下联系：`2565455406@qq.com`

特别欢迎反馈哪些技术发现真正有用、哪些推荐是噪声、哪些 capability 值得自动激活、激活边界是否过于保守或激进、新用户安装是否困难、Codex 检索是否节省搜索时间，以及 Windows/Codex 环境兼容性问题。
