"""Import frozen Bernini/Ditto handoff runs into separate existing score registries."""
import argparse
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from planner_harness.common import load, sha
from planner_harness.execution import signature, immutable
from experiments.results import import_video, inventory, register_plan, report
from run_bernini_benchmark import verify_completed


def ingest(repository, collection, run, renderer):
    run, collection = Path(run).resolve(), Path(collection).resolve()
    plan, runtime = load(run / "plan.json"), load(run / "runtime.json")
    if signature({k:v for k,v in plan.items() if k != "sha256"}) != plan["sha256"]:
        raise ValueError("Frozen plan changed")
    detected = "ditto" if "ditto" in runtime.get("renderer", "").lower() else "bernini" if "bernini_sources" in runtime and runtime.get("runner", "").startswith("bernini-") else None
    if renderer != detected:
        raise ValueError("Renderer differs from runtime identity")
    marker = collection / "renderer.json"
    if not marker.exists() and any((collection / "entries").glob("*/*/*/*.json")):
        raise ValueError("Use a fresh renderer collection; existing unlabeled entries require review")
    immutable(marker, {"renderer": renderer})
    tasks = inventory(repository)
    ready, positions = [], []
    # Validate every planned task and all available receipts before copying outputs.
    for case in plan["cases"]:
        key = (case["sample_id"], case["tier"])
        task = tasks[key]
        if task["request"] != case["prompt"] or task["source_sha256"] != case["source_sha256"]:
            raise ValueError("Run differs from current benchmark")
        if case["condition"] not in {"direct", "pe"}:
            raise ValueError("Unsupported handoff condition")
        folder = (run / "cases" / case["case_id"]).resolve()
        if not folder.is_relative_to(run / "cases"):
            raise ValueError("Unsafe case path")
        positions.append((task, case))
        receipt = folder / "result.json"
        if not receipt.exists() or load(receipt).get("status") != "complete":
            continue
        result, binding = load(receipt), load(folder / "input.json")
        verify_completed(folder, result)
        if binding["case"] != case or binding["plan_sha256"] != plan["sha256"] or binding["runtime_sha256"] != signature(runtime):
            raise ValueError("Case/plan/runtime binding changed")
        ready.append({"sample_id":case["sample_id"], "prompt_form":case["tier"],
            "method":case["condition"], "seed":case["seed"], "request":case["prompt"],
            "source_sha256":case["source_sha256"], "video":str(folder / "native.mp4"),
            "video_sha256":result["output_sha256"],
            "generation":{"renderer":renderer, "settings":plan["generation"], "runtime":runtime},
            "evidence":{"receipt":str(receipt), "receipt_sha256":sha(receipt),
                "input_sha256":result["input_sha256"], "runtime_sha256":signature(runtime)}})
    for task, case in positions:
        register_plan(collection, {"topics":[task], "arms":[case["condition"]],
            "seed_sequence":{"start":case["seed"]}})
    for row in ready:
        import_video(repository, collection, row)
    return report(repository, collection)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--renderer", choices=["bernini", "ditto"], required=True)
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--root", type=Path, required=True, help="Dedicated collection for this renderer")
    a=p.parse_args()
    result=ingest(ROOT,a.root,a.run,a.renderer)
    print(f"Ready {result['ready']}/{result['planned']}; {a.root.resolve() / 'index.html'}")

if __name__ == "__main__":
    main()
