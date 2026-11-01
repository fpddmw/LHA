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
    parser.add_argument("--execute", action="store_true", help="Live API call; use only after user resumes experiments")
    args = parser.parse_args()
    from planner_harness.video import Video
    from evaluation.creative import prepare_final_request, judge_candidate
    output = Path(args.output)
    source, candidate = Video(args.source, output).info, Video(args.candidate, output).info
    request = Path(args.request_file).read_text(encoding="utf-8")
    if args.execute:
        judge_candidate(request, source, candidate, output)
        print("Independent judgment saved.")
    else:
        packet, images = prepare_final_request(request, source, candidate, output)
        print(json.dumps({"status": "request_export_only", "model": "glm5.3flash", "images": len(images),
                          "request": str(output / "evidence/request.json"), "model_calls": 0}))


if __name__ == "__main__":
    main()
