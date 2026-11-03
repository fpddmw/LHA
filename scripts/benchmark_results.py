"""Import verified videos into the common sample/form/method/seed result view."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main():
    from experiments.results import import_manifest, import_bernini, report, METHODS, prepare_evaluation, score_evaluation, append_evaluation
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=["import", "import-bernini", "export-shard", "report", "prepare-evaluation", "append-evaluation", "score-evaluation"])
    p.add_argument("--root", type=Path, default=ROOT / "out/benchmark_results")
    p.add_argument("--manifest", type=Path)
    p.add_argument("--run", type=Path)
    p.add_argument("--output",type=Path)
    p.add_argument("--method", nargs="+", choices=METHODS)
    p.add_argument("--seed", nargs="+", type=int)
    p.add_argument("--split", nargs="+", choices=["train", "validation", "test"])
    p.add_argument("--prompt-form", nargs="+", choices=["short", "long"])
    p.add_argument("--review-mode", nargs="+", choices=["critic","planner","legacy"])
    p.add_argument("--evaluation-id")
    p.add_argument("--execute", action="store_true")
    p.add_argument("--budget-config", type=Path)
    args = p.parse_args()
    imported = []
    if args.command == "import":
        if not args.manifest: p.error("import requires --manifest")
        imported = import_manifest(ROOT, args.root, args.manifest)
    elif args.command == "import-bernini":
        if not args.run: p.error("import-bernini requires --run")
        imported = import_bernini(ROOT, args.root, args.run)
    elif args.command == "export-shard":
        if not args.run or not args.output:p.error("export-shard requires --run and --output")
        from experiments.results import export_shard
        print(json.dumps({"manifest":str(export_shard(ROOT,args.root,args.run,args.output))}));return
    elif args.command == "prepare-evaluation":
        prepare_evaluation(ROOT, args.root, evaluation_id=args.evaluation_id)
    elif args.command == "append-evaluation":
        append_evaluation(ROOT, args.root)
    elif args.command == "score-evaluation":
        if not args.execute: p.error("Live scoring requires --execute")
        from planner_harness.common import load
        from planner_harness import accounting
        from experiments.results import ensure_evaluation
        active = ensure_evaluation(ROOT, args.root, evaluation_id=args.evaluation_id)
        from planner_harness.supervisor import maybe_supervise_cli
        if maybe_supervise_cli(active[0], [__file__, *sys.argv[1:]]): return
        score_evaluation(ROOT, args.root, load(args.budget_config) if args.budget_config else None)
    # The unique landing page always retains the complete collection. Optional
    # filters affect the console count, never hide other results in index.html.
    result = report(ROOT, args.root)
    selected = [r for r in result["results"] if (not args.method or r["method"] in args.method)
        and (not args.seed or r["seed"] in args.seed) and (not args.split or r["split"] in args.split)
        and (not args.prompt_form or r["prompt_form"] in args.prompt_form)
        and (not args.review_mode or r.get("review_mode","shared") in {*args.review_mode,"shared"})]
    print(json.dumps({"imported": len(imported), "ready": sum(r["status"] == "ready" for r in selected), "planned": len(selected),
                      "index": str(args.root.resolve() / "index.html")}, ensure_ascii=False))


if __name__ == "__main__":
    from planner_harness.supervisor import cli_entry
    cli_entry(main)
