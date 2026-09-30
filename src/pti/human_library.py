from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


HUMAN_CATEGORY_LABELS = {
    "USED": "已经实际使用",
    "USABLE": "现在可以使用",
    "ADOPTED_METHOD": "已采用的方法",
    "WAITING_VALIDATION": "已批准，等待验证",
    "VALIDATING": "正在处理",
    "HUMAN_DECISION": "需要你决定",
    "WATCHLIST": "继续观察",
    "NOT_ADOPTED": "暂不采用",
    "VALIDATION_FAILED": "验证未通过",
    "ARCHIVED": "已归档",
}

METHOD_SOURCES = {"bmad-code-org/BMAD-METHOD", "github/spec-kit"}

EXPLICIT_NON_ADOPTIONS = {
    "FoundationAgents/MetaGPT": {
        "reason": "与现有 Codex、技能和子任务协作高度重复，且没有代码、运行或比较证据证明新增价值。",
        "next_step": "不安装；只有出现明确且现有能力无法解决的多智能体需求时才重新评审。",
    },
    "langchain-ai/langchain": {
        "reason": "覆盖面广但与现有 Agent、技能和插件能力高度重叠，当前没有经验证的增量能力。",
        "next_step": "不加入当前运行栈；仅在具体集成需求出现时重新比较。",
    },
}

WATCHLIST_ITEMS = {
    "ComposioHQ/awesome-claude-skills": {
        "kind": "KNOWLEDGE_REFERENCE",
        "reason": "它是第三方能力索引，只能帮助发现方向，不能证明其中条目安全、兼容或值得安装。",
        "next_step": "保留为人工检索参考；任何条目仍需独立审查。",
    },
    "cased/kit": {
        "kind": "KNOWLEDGE_REFERENCE",
        "reason": "代码库映射和符号检索方向相关，但没有本机验证或比较证据证明优于现有检索能力。",
        "next_step": "观察后续证据；出现大型代码库检索瓶颈时再做隔离比较。",
    },
    "chunkhound/chunkhound": {
        "kind": "PROJECT",
        "reason": "语义索引和 MCP 检索可能有用，但部署、数据边界、资源占用和相对收益均未验证。",
        "next_step": "保持观察，不启动索引服务或 MCP。",
    },
    "gmickel/flow-next": {
        "kind": "KNOWLEDGE_REFERENCE",
        "reason": "新鲜上下文 worker 和跨 Agent 交接值得参考，但没有形成独立采用的方法，也没有运行证据。",
        "next_step": "保留为工作流比较资料，不替换现有 Codex 流程。",
    },
    "headroomlabs-ai/headroom": {
        "kind": "PROJECT",
        "reason": "上下文压缩方向相关，但压缩正确性、安全边界和本机收益尚未验证。",
        "next_step": "保持观察；只有上下文成本成为明确瓶颈时再做隔离测试。",
    },
    "volcengine/MineContext": {
        "kind": "PROJECT",
        "reason": "主动上下文体验有参考价值，但与现有能力重叠，隐私、权限和可靠性证据不足。",
        "next_step": "保持观察，不启动桌面采集或后台服务。",
    },
}

SPECIAL_CANDIDATES = {
    "coleam00/archon": {
        "reason": "已进行受控边界审查，但缺少固定版本、回滚路径、隔离执行证据和明确增量；安全激活流程在安装前终止。",
        "next_step": "仅当上游提供可固定版本、可回滚隔离路径，并出现现有流程无法满足的具体需求时重新评审。",
    },
    "TauricResearch/TradingAgents": {
        "reason": "金融多智能体方向可能相关，但代码、数据源、安全边界和真实效果均未验证，且涉及敏感交易范围。",
        "next_step": "由用户决定是否只用公开或合成数据进入隔离研究；不得接入真实交易系统。",
    },
    "nieledran/backtesting-engine": {
        "reason": "用户已允许后续隔离评估；当前仍未安装，需先验证依赖、凭据边界、回滚和相对增量。",
        "next_step": "系统后续仅在公开或合成数据环境中继续审查，不接入 broker、账户或受保护项目。",
    },
}


def _queue_attempted(queue_records: list[dict[str, Any]]) -> bool:
    return any(
        int(record.get("attempt_count") or 0) > 0
        or record.get("status") in {"PROCESSING", "FAILED_TERMINAL"}
        for record in queue_records
    )


def load_human_library_evidence(
    db_path: str | Path,
) -> tuple[dict[int, dict[str, Any]], dict[int, list[dict[str, Any]]]]:
    """Load the latest owner feedback and activation queue facts read-only."""
    feedback: dict[int, dict[str, Any]] = {}
    queues: dict[int, list[dict[str, Any]]] = {}
    path = Path(db_path).resolve()
    if not path.is_file():
        return feedback, queues
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if "user_feedback" in tables:
            rows = connection.execute("""
                SELECT f.github_repository_id, f.label, f.note, f.created_at
                FROM user_feedback f
                JOIN (
                    SELECT github_repository_id, MAX(id) AS id
                    FROM user_feedback
                    GROUP BY github_repository_id
                ) latest ON latest.id = f.id
            """).fetchall()
            feedback = {int(row["github_repository_id"]): dict(row) for row in rows}
        if "activation_queue" in tables:
            for row in connection.execute("SELECT * FROM activation_queue ORDER BY id"):
                queues.setdefault(int(row["repository_id"]), []).append(dict(row))
    finally:
        connection.close()
    return feedback, queues


def project_human_library_item(
    card: dict[str, Any],
    latest_feedback: dict[str, Any] | None = None,
    queue_records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Derive the human-facing library state without rewriting source history."""
    repository = str(card.get("repository") or "")
    state = str(card.get("activation_state") or "")
    feedback = latest_feedback or card.get("human_decision") or None
    queue = queue_records or []
    category = "WATCHLIST"
    item_kind = "KNOWLEDGE_REFERENCE"
    reason = "当前只有评审或参考证据，没有安装、可运行或实际采用证据。"
    next_step = "继续观察；出现明确需求和新增证据后再评审。"
    processing_state = "NONE"
    human_action_required = False

    if state == "USED" or card.get("real_use_outcome") == "USED_SUCCESSFULLY":
        category = "USED"
        item_kind = "CAPABILITY"
        reason = "已有受控安装、隔离测试和真实任务成功使用证据。"
        next_step = "在授权范围内继续复用，并保留现有安全边界。"
    elif state == "TRIAL_ENABLED":
        category = "USABLE"
        item_kind = "CAPABILITY"
        reason = "受控试用已启用，当前具备可调用入口，但还没有真实使用证据。"
        next_step = "在合适的低风险任务中使用并记录结果。"
    elif repository in METHOD_SOURCES and card.get("method_adoption_state") == "ADOPTED":
        category = "ADOPTED_METHOD"
        item_kind = "METHOD_SOURCE"
        reason = "该来源至少有一个方法同时具备可验证的工作流机制和真实使用证据。"
        next_step = "继续通过已记录的工作流机制使用，并保留使用证据。"
    elif repository in METHOD_SOURCES:
        category = "WATCHLIST"
        item_kind = "METHOD_SOURCE"
        reason = "已提炼出方法参考，但没有发现可验证的本地工作流机制和对应使用证据。"
        next_step = "保留为知识参考；只有真实进入工作流后才能标记为已采用。"
    elif feedback and feedback.get("label") == "APPROVE_FOR_REVIEW":
        active = any(record.get("status") == "PROCESSING" for record in queue)
        category = "VALIDATING" if active else "WAITING_VALIDATION"
        item_kind = "CANDIDATE"
        processing_state = "IN_PROGRESS" if active else "APPROVED_WAITING_VALIDATION"
        reason = SPECIAL_CANDIDATES.get(repository, {}).get(
            "reason", "用户已允许后续隔离评估；这不是安装或采用证明。"
        )
        next_step = SPECIAL_CANDIDATES.get(repository, {}).get(
            "next_step", "等待系统按安全边界继续验证。"
        )
    elif feedback and feedback.get("label") == "WATCH":
        category = "WATCHLIST"
        item_kind = "CANDIDATE"
        reason = "用户已经选择继续观察；当前不安装、不运行。"
        next_step = "等待新的项目证据或明确需求。"
    elif feedback and feedback.get("label") in {"NOT_USEFUL", "TOO_RISKY"}:
        category = "NOT_ADOPTED"
        item_kind = "PROJECT"
        reason = "用户已经明确选择暂不采用。"
        next_step = "保留历史记录，不再主动推进。"
    elif card.get("semantic_action") in {"IGNORE", "ARCHIVE"}:
        category = "ARCHIVED" if card.get("semantic_action") == "ARCHIVE" else "NOT_ADOPTED"
        item_kind = "PROJECT"
        reason = "最终 Chancellor 判断不继续采用；没有安装或运行。"
        next_step = "保留决策证据；只有出现实质新证据时重新评审。"
    elif state == "BLOCKED_HUMAN":
        category = "HUMAN_DECISION"
        item_kind = "CANDIDATE"
        human_action_required = True
        reason = SPECIAL_CANDIDATES.get(repository, {}).get(
            "reason", "该候选涉及需要用户明确授权的风险或集成边界。"
        )
        next_step = SPECIAL_CANDIDATES.get(repository, {}).get(
            "next_step", "等待用户选择继续隔离评估、观察或不采用。"
        )
    elif state in {"FAILED_WITH_EXPLAINED_REASON", "FAILED_TERMINAL"} and _queue_attempted(queue):
        category = "VALIDATION_FAILED"
        item_kind = "CANDIDATE"
        processing_state = "STOPPED_SAFELY"
        reason = SPECIAL_CANDIDATES.get(repository, {}).get(
            "reason", "受控验证已经尝试并安全停止，未形成可运行能力。"
        )
        next_step = SPECIAL_CANDIDATES.get(repository, {}).get(
            "next_step", "只有阻断条件发生实质变化时才重新验证。"
        )
    elif repository in EXPLICIT_NON_ADOPTIONS:
        category = "NOT_ADOPTED"
        item_kind = "PROJECT"
        reason = EXPLICIT_NON_ADOPTIONS[repository]["reason"]
        next_step = EXPLICIT_NON_ADOPTIONS[repository]["next_step"]
    elif any(record.get("status") in {"PENDING", "PROCESSING", "RETRYABLE"} for record in queue):
        category = "VALIDATING"
        item_kind = "CANDIDATE"
        processing_state = "IN_PROGRESS"
        reason = "候选正在受控验证；尚未形成可用或真实使用证据。"
        next_step = "查看验证阶段和阻断原因。"
    elif repository in WATCHLIST_ITEMS:
        category = "WATCHLIST"
        item_kind = WATCHLIST_ITEMS[repository]["kind"]
        reason = WATCHLIST_ITEMS[repository]["reason"]
        next_step = WATCHLIST_ITEMS[repository]["next_step"]
    elif state in {"QUARANTINE_READY", "VALIDATING"}:
        category = "VALIDATING"
        item_kind = "CANDIDATE"
        processing_state = "IN_PROGRESS"
        reason = "候选已进入受控验证，但尚未形成可用或实际使用证据。"
        next_step = "完成隔离验证并记录结果。"
    elif state in {"TESTED_NOT_ADOPTED", "KEEP_REFERENCE_ONLY"}:
        category = "NOT_ADOPTED"
        item_kind = "PROJECT"
        reason = "现有结论明确为评审后暂不采用。"
        next_step = "保留历史记录，只有新增证据时重新评审。"
    elif card.get("semantic_action") == "REFERENCE_ONLY":
        category = "WATCHLIST"
        item_kind = "KNOWLEDGE_REFERENCE"
        reason = "最终 Chancellor 判断仅作知识参考，不代表安装、采用或可运行。"
        next_step = "按具体任务查阅参考；不自动部署整包。"

    installed = state in {"TRIAL_ENABLED", "USED"}
    runnable = installed and card.get("trial_status") in {"ENABLED", "ENABLED_CONTROLLED"}
    return {
        **card,
        "human_category": category,
        "human_category_label": HUMAN_CATEGORY_LABELS[category],
        "item_kind": item_kind,
        "classification_reason": reason,
        "next_step": next_step,
        "human_action_required": human_action_required,
        "processing_state": processing_state,
        "installed": installed,
        "runnable": runnable,
    }
