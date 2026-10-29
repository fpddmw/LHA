"""Start or resume the continuous, model-led Planner loop."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_planner_harness import main

if __name__ == "__main__":
    if "--mode" not in sys.argv:
        sys.argv[1:1] = ["--mode", "loop"]
    raise SystemExit(main())
