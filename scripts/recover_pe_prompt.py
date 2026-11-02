"""Inspect or resume a PE tokenizer refusal using its original budget and videos."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main():
    from experiments.recovery import recover_pe_prompt
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--topic", required=True)
    parser.add_argument("--device", required=True, help="Original worker directory ID")
    parser.add_argument("--reason", default="Inspected tokenizer refusal before GPU generation")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    print(json.dumps(recover_pe_prompt(args.output, args.topic, args.device, args.reason,
                                      execute=args.execute), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
