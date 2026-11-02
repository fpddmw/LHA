"""Explicit offline request export or later authorized independent scoring; no batch launcher."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--request-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--judge", choices=["glm5.3flash", "sonnet-5.5high"], default="glm5.3flash")
    parser.add_argument("--experiment-profile", type=Path, help="Shared profile used by the comparison cohort")
    parser.add_argument("--plan", type=Path, help="Frozen original-task plan shared by all methods and judges")
    parser.add_argument("--execute", action="store_true", help="Live API call; use only after user resumes experiments")
    parser.add_argument("--budget-config",type=Path)
    args = parser.parse_args()
    budget_scope=None
    if args.budget_config:
        from planner_harness.accounting import install,scope
        policy=json.loads(args.budget_config.read_text())
        budget_root=install(Path(args.output)/'compute-accounting',policy,require_live=True,required_quotes=('compute:features','compute:temporal'))
        budget_scope=scope(budget_root,'standalone-final-compute','independent')
    if args.experiment_profile:
        from planner_harness.creative import verify_experiment
        from planner_harness.execution import immutable
        immutable(Path(args.output) / "experiment-profile.json", verify_experiment(args.experiment_profile, ROOT))
    from planner_harness.video import Video
    from evaluation.creative import prepare_final_request, judge_candidate, make_judge, judge_identity
    output = Path(args.output)
    source, candidate = Video(args.source, output).info, Video(args.candidate, output).info
    request = Path(args.request_file).read_text(encoding="utf-8")
    plan = json.loads(args.plan.read_text(encoding="utf-8")) if args.plan else None
    if args.execute:
        if plan is None:
            parser.error("--execute requires --plan; use run_low_high_eval.py plan first")
        result=judge_candidate(request, source, candidate, output, model=make_judge(args.judge), plan=plan)
        from evaluation.final_suite import automatic
        from planner_harness.execution import immutable
        immutable(output/'suite.json',{**result,'automatic':automatic(source,candidate,plan,output/'automatic-metrics',accounting_scope=budget_scope)})
        print("Independent judgment saved.")
    else:
        packet, images = prepare_final_request(request, source, candidate, output, plan=plan)
        print(json.dumps({"status": "request_export_only", **judge_identity(args.judge), "images": len(images),
                          "request": str(output / "evidence/request.json"), "model_calls": 0}))


if __name__ == "__main__":
    from planner_harness.supervisor import cli_entry
    cli_entry(main)
