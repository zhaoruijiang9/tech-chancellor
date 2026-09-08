import json
from pathlib import Path
from typing import Any

from .capability_library import _card, _read_rows


STATUS_LABELS = {
    "TRIAL_ENABLED": "已安装，可用",
    "USED": "已实际使用",
    "ACTIVE_PATTERN": "已启用的方法",
    "KEEP_REFERENCE_ONLY": "已研究，当前不值得安装",
    "TESTED_NOT_ADOPTED": "已检查，暂不采用",
    "BLOCKED_HUMAN": "需要你批准后才能进一步启用",
    "FAILED_WITH_EXPLAINED_REASON": "已检查，因明确限制暂未启用",
}


def _usage(root: Path) -> dict[str, dict[str, Any]]:
    path = root / "config" / "human_capability_usage.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _with_usage(root: Path, card: dict[str, Any]) -> dict[str, Any]:
    usage = _usage(root).get(card["repository"], {})
    defaults = {
        "human_summary": card["capability_name"],
        "when_to_use": [card["problem_solved"]],
        "how_to_ask_codex": [f"帮我判断 {card['repository']} 对这个任务是否值得参考。"],
        "expected_outputs": ["面向当前任务的判断和证据"],
        "user_entrypoint": "直接描述你的目标，Codex 会判断是否相关。",
        "automatic_use_policy": "由 Codex 按任务相关性判断。",
        "main_limitations": [card["limitations"].get("IS_IT_ACTUALLY_BETTER", "证据仍有限。")],
    }
    return {**card, **{key: usage.get(key, value) for key, value in defaults.items()},
            "human_status": STATUS_LABELS.get(card["activation_state"], card["activation_state"])}


def build_human_toolbox(root: str | Path, db_path: str | Path | None = None) -> dict[str, Any]:
    root = Path(root).resolve()
    cards = [_with_usage(root, _card(row)) for row in _read_rows(db_path or root / "state" / "intelligence.db")]
    direct = [card for card in cards if card["activation_state"] in {"TRIAL_ENABLED", "USED"}]
    patterns = [card for card in cards if card["activation_state"] == "ACTIVE_PATTERN"]
    reference = [card for card in cards if card["activation_state"] not in {"TRIAL_ENABLED", "USED", "ACTIVE_PATTERN", "BLOCKED_HUMAN"}]
    human_gate = [card for card in cards if card["activation_state"] == "BLOCKED_HUMAN"]

    lines = ["# 我现在能用什么？", "", "这份清单由 PTI 当前能力库自动生成；项目状态以数据库为准。", ""]
    def section(title: str, items: list[dict[str, Any]]) -> None:
        lines.extend([f"## {title}", ""])
        if not items:
            lines.append("暂无。\n")
            return
        for card in items:
            lines.extend([f"### {card['repository']}：{card['human_summary']}",
                          f"- 状态：{card['human_status']}",
                          f"- 适合：{'；'.join(card['when_to_use'])}",
                          f"- 你可以说：{' / '.join(card['how_to_ask_codex'])}",
                          f"- 会得到：{'；'.join(card['expected_outputs'])}",
                          f"- 入口：{card['user_entrypoint']}",
                          f"- 自动程度：{card['automatic_use_policy']}",
                          f"- 限制：{'；'.join(card['main_limitations'])}", ""])

    section("已安装 / 可以直接用", direct)
    section("已启用的方法 / 工作模式", patterns)
    section("已研究但当前不值得安装", reference)
    section("需要我批准才能进一步启用", human_gate)
    lines.extend(["## 结果在哪里？", "", "需要生成文件的能力会在 PTI 的 `reports/` 或能力专属输出目录留下文件；Codex 会在交付时给出可直接打开的完整路径。", ""])
    output = root / "MY_CAPABILITIES.md"
    output.write_text("\n".join(lines), encoding="utf-8")
    generated = root / "library" / "generated"
    generated.mkdir(parents=True, exist_ok=True)
    (generated / "human_toolbox.json").write_text(json.dumps({"count": len(cards), "cards": cards}, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "HUMAN_TOOLBOX_BUILT", "count": len(cards), "entrypoint": str(output), "directly_usable": len(direct), "active_patterns": len(patterns), "human_gate": len(human_gate)}
