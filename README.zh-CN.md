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
