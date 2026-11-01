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
    parser.add_argument("--execute", action="store_true", help="Live API call; use only after user resumes experiments")
    args = parser.parse_args()
    if args.experiment_profile:
        from planner_harness.creative import verify_experiment
        from planner_harness.execution import immutable
        immutable(Path(args.output) / "experiment-profile.json", verify_experiment(args.experiment_profile, ROOT))
    from planner_harness.video import Video
    from evaluation.creative import prepare_final_request, judge_candidate, make_judge, judge_identity
    output = Path(args.output)
    source, candidate = Video(args.source, output).info, Video(args.candidate, output).info
    request = Path(args.request_file).read_text(encoding="utf-8")
    if args.execute:
        judge_candidate(request, source, candidate, output, model=make_judge(args.judge))
        print("Independent judgment saved.")
    else:
        packet, images = prepare_final_request(request, source, candidate, output)
        print(json.dumps({"status": "request_export_only", **judge_identity(args.judge), "images": len(images),
                          "request": str(output / "evidence/request.json"), "model_calls": 0}))


if __name__ == "__main__":
    main()
