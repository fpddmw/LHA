#!/usr/bin/env python3
"""Run the versioned source-aware benchmark evaluator from any working directory."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from evaluation.cli import main

if __name__ == "__main__":
    sys.exit(main())
