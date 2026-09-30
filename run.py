import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from pti.cli import record_feedback, run_once
from pti.stage_b import run_stage_b
from pti.packet_lifecycle import active_pending_count
from pti.health import health_report
from pti.capability_library import build_library
from pti.capability_search import search_capabilities
from pti.human_toolbox import build_human_toolbox
from pti.bootstrap import initialize_project
from pti.dashboard_server import serve_dashboard
from pti.windows_shortcut import install_desktop_shortcut
from pti.capability_intelligence import CapabilityStore
from pti.storage import Database
from pti.upstream_intelligence import GitHubFingerprintProvider, check_upstream
from pti.upstream_review import CodexDeltaReviewer, review_pending_deltas
from pti.activation_worker import enqueue_selected_pilots, run_activation_worker, search_active_index
from pti.activation_readiness import audit_current_library, second_pilot_candidates
from pti import __version__


def main() -> int:
    parser = argparse.ArgumentParser(description="Manual Phase 1 technology intelligence run")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("action", nargs="?", choices=["init", "scan", "stage-b", "repair-stranded-candidates", "activation-run", "activation-status", "activation-search", "activation-readiness", "feedback", "pending-count", "health", "build-library", "my-capabilities", "search-capabilities", "dashboard", "install-shortcut", "migrate-capabilities", "check-upstream", "review-upstream", "review-delta"], default="scan")
    parser.add_argument("repo", nargs="?")
    parser.add_argument("label", nargs="?")
    parser.add_argument("note", nargs="?", default="")
    parser.add_argument("--config", default="config/discovery.json")
    parser.add_argument("--capability-profile", default="config/local_capability_profile.json")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--apply", action="store_true", help="apply a bounded single-candidate repair after dry-run inspection")
    parser.add_argument("--problem", default="")
    parser.add_argument("--task-context", default="")
    parser.add_argument("--project-context", default="")
    parser.add_argument("--current-capability", action="append", default=[])
    parser.add_argument("--constraint", action="append", default=[])
    parser.add_argument("--project-label", default="")
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--format", choices=["json"], default="json")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--browser", action="store_true", help="use a normal browser window instead of app mode")
    parser.add_argument("--open-obsidian", action="store_true")
    parser.add_argument("--force-upstream", action="store_true")
    parser.add_argument("--review-id", type=int)
    parser.add_argument("--review-outcome", default="")
    parser.add_argument("--review-evidence", default="")
    args = parser.parse_args()
    root = Path(__file__).parent
    if args.action == "repair-stranded-candidates":
        if not args.repo:
            parser.error("repair-stranded-candidates requires one canonical repository name")
        from pti.candidate_pipeline import repair_stranded_candidates, stranded_candidate_summary
        from pti.github_api import GitHubClient, RequestBudget
        Database(root / "state/intelligence.db").initialize()
        result = repair_stranded_candidates(root, args.repo, dry_run=not args.apply,
                    client=GitHubClient(budget=RequestBudget(4)) if args.apply else None)
        result["remaining_stranded"] = stranded_candidate_summary(root)["count"]
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] in {"REPAIR_READY", "REPAIR_NEEDS_EVIDENCE_REFRESH", "RESUMED", "ALREADY_PENDING", "ALREADY_DECIDED"} else 1
    if args.action == "activation-readiness":
        db = Database(root / "state" / "intelligence.db")
        db.initialize()
        result = audit_current_library(db)
        result["second_pilot_candidates"] = second_pilot_candidates(db)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if not result["unclassified"] else 1
    if args.action in {"activation-run", "activation-status", "activation-search"}:
        if args.action == "activation-search":
            if not args.repo:
                parser.error("activation-search requires a query")
            print(json.dumps({"query": args.repo, "results": search_active_index(root, args.repo),
                              "warning": "Linked third-party skills are unreviewed and not installed."},
                             ensure_ascii=False, indent=2))
            return 0
        db = Database(root / "state" / "intelligence.db")
        db.initialize()
        if args.action == "activation-status":
            print(json.dumps({"jobs": db.list_activation_queue()}, ensure_ascii=False, indent=2))
            return 0
        selected = enqueue_selected_pilots(db, limit=1)
        results = run_activation_worker(root, db, limit=args.limit)
        if any(item["status"] == "SUCCEEDED" for item in results):
            build_human_toolbox(root)
        print(json.dumps({"selected": selected, "results": results}, ensure_ascii=False, indent=2))
        return 0 if all(item["status"] in {"SUCCEEDED", "ALREADY_ACTIVE_OR_LOCKED"} for item in results) else 1
    if args.action in {"migrate-capabilities", "check-upstream", "review-upstream", "review-delta"}:
        db_path = root / "state" / "intelligence.db"
        Database(db_path).initialize()
        store = CapabilityStore(db_path)
        if args.action == "review-delta":
            if args.review_id is None:
                parser.error("review-delta requires --review-id")
            from pti.models import utc_now
            store.complete_delta_review(args.review_id, args.review_outcome, args.review_evidence, utc_now())
            print(json.dumps({"status": "REVIEW_RECORDED", "review_id": args.review_id}, ensure_ascii=False))
            return 0
        migration = store.migrate_reviewed_sources()
        if args.action == "migrate-capabilities":
            print(json.dumps({"status": "MIGRATION_COMPLETE", **migration}, ensure_ascii=False, indent=2))
            return 0
        if args.action == "review-upstream":
            result = review_pending_deltas(store, CodexDeltaReviewer(root), limit=args.limit)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result["failed"] == 0 and result["skipped_exhausted"] == 0 else 1
        result = check_upstream(store, GitHubFingerprintProvider(), force=args.force_upstream)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["failures"] == 0 else 1
    if args.action == "init":
        result = initialize_project(root, root / args.config, root / args.capability_profile)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.action == "dashboard":
        if args.host != "127.0.0.1":
            parser.error("dashboard only permits localhost binding: 127.0.0.1")
        return serve_dashboard(root, host=args.host, port=args.port, open_browser=not args.no_browser,
                               desktop=not args.browser, open_obsidian=args.open_obsidian)
    if args.action == "install-shortcut":
        result = install_desktop_shortcut(root)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.action == "pending-count":
        print(active_pending_count(root / "chancellor_pending"))
        return 0
    if args.action == "health":
        result = health_report(root)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] in {"HEALTHY", "DEGRADED_HISTORY_ONLY", "DEGRADED"} else 1
    if args.action == "build-library":
        result = build_library(root)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.action == "my-capabilities":
        result = build_human_toolbox(root)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.action == "search-capabilities":
        result = search_capabilities(root / "state" / "intelligence.db", problem=args.problem,
                                     task_context=args.task_context, project_context=args.project_context,
                                     current_capabilities=args.current_capability, constraints=args.constraint,
                                     limit=args.limit, project_label=args.project_label)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.action == "stage-b":
        result = run_stage_b(root, limit=args.limit, repository=args.repo)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] in {"CHANCELLOR_SUCCESS", "CHANCELLOR_SUCCESS_NO_PENDING"} else 1
    if args.action == "feedback":
        if not args.repo or not args.label:
            parser.error("feedback requires REPO LABEL [NOTE]")
        record_feedback(root, args.repo, args.label, args.note)
        print(json.dumps({"status": "FEEDBACK_RECORDED", "repository": args.repo, "label": args.label}, ensure_ascii=False))
        return 0
    result = run_once(root, root / args.config, root / args.capability_profile, dry_run=True)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in {"PASS", "PARTIAL", "SCAN_SUCCESS", "SCAN_SUCCESS_NO_HIGH_SIGNAL"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
