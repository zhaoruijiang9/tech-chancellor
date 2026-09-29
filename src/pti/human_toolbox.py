import json
from pathlib import Path
from typing import Any

from .capability_library import _card, _read_rows
from .human_library import load_human_library_evidence, project_human_library_item


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
    from .dashboard_read_model import DashboardReadModel

    root = Path(root).resolve()
    db_path = Path(db_path or root / "state" / "intelligence.db")
    entities = DashboardReadModel(root, db_path=db_path)._entity_snapshot()
    feedback, queues = load_human_library_evidence(db_path)
    cards = []
    for row in _read_rows(db_path):
        repository_id = int(row["github_repository_id"])
        cards.append(project_human_library_item(
            _with_usage(root, _card(row)), feedback.get(repository_id), queues.get(repository_id, [])
        ))
    direct = entities["capability_entities"]
    patterns = entities["method_entities"]
    pending = [card for card in cards if card["human_category"] in {"WAITING_VALIDATION", "VALIDATING", "HUMAN_DECISION"}]
    reference = [card for card in cards if card["human_category"] in {"WATCHLIST", "NOT_ADOPTED", "VALIDATION_FAILED", "ARCHIVED"}]

    lines = ["# 我现在能用什么？", "", "这份清单由 PTI 当前能力库自动生成；项目状态以数据库为准。", ""]
    def asset_section(title: str, items: list[dict[str, Any]]) -> None:
        lines.extend([f"## {title}", ""])
        if not items:
            lines.append("暂无。\n")
            return
        for item in items:
            sources = [entry["source_name"] for entry in item.get("implementations", []) if entry.get("source_name")]
            if item.get("source_name"):
                sources.append(item["source_name"])
            lines.extend([f"### {item['name']}", f"- 说明：{item['description']}",
                          f"- 来源：{'、'.join(sources) or '本地工作流'}",
                          f"- 状态：{'、'.join(item.get('personal_states', [])) if item.get('capability_id') else '已记录机制与实际使用证据'}", ""])

    def section(title: str, items: list[dict[str, Any]]) -> None:
        lines.extend([f"## {title}", ""])
        if not items:
            lines.append("暂无。\n")
            return
        for card in items:
            lines.extend([f"### {card['repository']}：{card['human_summary']}",
                          f"- 状态：{card['human_category_label']}",
                          f"- 保留原因：{card['classification_reason']}",
                          f"- 适合：{'；'.join(card['when_to_use'])}",
                          f"- 你可以说：{' / '.join(card['how_to_ask_codex'])}",
                          f"- 会得到：{'；'.join(card['expected_outputs'])}",
                          f"- 入口：{card['user_entrypoint']}",
                          f"- 自动程度：{card['automatic_use_policy']}",
                          f"- 限制：{'；'.join(card['main_limitations'])}", ""])

    asset_section("我的能力", direct)
    asset_section("已采用的方法", patterns)
    section("等待验证 / 正在验证 / 需要你决定", pending)
    section("观察与归档", reference)
    lines.extend(["## 结果在哪里？", "", "需要生成文件的能力会在 PTI 的 `reports/` 或能力专属输出目录留下文件；Codex 会在交付时给出可直接打开的完整路径。", ""])
    output = root / "MY_CAPABILITIES.md"
    output.write_text("\n".join(lines), encoding="utf-8")
    generated = root / "library" / "generated"
    generated.mkdir(parents=True, exist_ok=True)
    (generated / "human_toolbox.json").write_text(json.dumps({"count": len(cards), "cards": cards,
        "capabilities": direct, "methods": patterns}, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "HUMAN_TOOLBOX_BUILT", "count": len(cards), "entrypoint": str(output),
            "directly_usable": len(direct), "adopted_methods": len(patterns),
            "processing": sum(card["human_category"] == "VALIDATING" for card in pending),
            "human_gate": sum(card["human_category"] == "HUMAN_DECISION" for card in pending)}
