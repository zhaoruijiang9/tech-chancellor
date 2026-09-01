import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from pti.cli import record_feedback, run_once
from pti.stage_b import run_stage_b
from pti.packet_lifecycle import active_pending_count
from pti.health import health_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Manual Phase 1 technology intelligence run")
    parser.add_argument("action", nargs="?", choices=["scan", "stage-b", "feedback", "pending-count", "health"], default="scan")
    parser.add_argument("repo", nargs="?")
    parser.add_argument("label", nargs="?")
    parser.add_argument("note", nargs="?", default="")
    parser.add_argument("--config", default="config/discovery.json")
    parser.add_argument("--capability-profile", default="config/local_capability_profile.json")
    parser.add_argument("--dry-run", action="store_true", default=True)
    args = parser.parse_args()
    root = Path(__file__).parent
    if args.action == "pending-count":
        print(active_pending_count(root / "chancellor_pending"))
        return 0
    if args.action == "health":
        result = health_report(root)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] in {"HEALTHY", "DEGRADED_HISTORY_ONLY"} else 1
    if args.action == "stage-b":
        result = run_stage_b(root)
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
