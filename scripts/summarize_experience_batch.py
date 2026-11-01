"""Export saved development evidence without importing renderers or model clients."""
import argparse
import importlib.util
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    module_file = Path(__file__).resolve().parents[1] / "src/planner_harness/experience_usage.py"
    spec = importlib.util.spec_from_file_location("experience_usage_export", module_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.export_batch(args.manifest, args.output)
    print(f"Recorded {result['specified_runs']} specified runs: {result['record_counts']}")


if __name__ == "__main__":
    main()
