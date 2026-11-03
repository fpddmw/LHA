"""Run offline regression modules in isolated processes with concise results.

Current tests exercise the API creative loop. Historical protocols remain available
through --suite historical; they are not the current protocol's acceptance tests.
Only tests defined in each module are loaded, avoiding imported fixture duplicates.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import contextlib
import importlib
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
CURRENT = (
    "test_api_backend",
    "test_chatgpt_subscription",
    "test_configuration_boundaries",
    "test_chain_integration",
    "test_public_campaign",
    "test_pre_experience_parallel",
    "test_fixed_budget_completion",
    "test_review_modes",
    "test_review_experiments",
    "test_loop_protocol_upgrade",
    "test_planner_iteration",
    "test_loop_engineering",
    "test_interrupted_model_recovery",
    "test_engineering_cleanup",
    "test_creative_loop",
    "test_creative_repairs",
    "test_resource_accounting",
    "test_server_runtime",
    "test_planner_worker",
    "test_experiment_engineering",
    "test_experiment_campaign",
    "test_pe_loop",
    "test_dual_model_campaign",
    "test_pe_budget_scoring_entry",
    "test_unified_results",
    "test_creative_benchmark",
    "test_creative_benchmark_schedule",
    "test_final_review_remediation",
    "test_low_high",
    "test_evaluation_v2",
    "test_evaluation_reporting",
    "test_metric_registry",
    "test_lineage_analysis",
    "test_continuation_maintenance",
    "test_experience_curation",
    "test_experience_layers",
    "test_experience_contributions",
    "test_experience_families",
    "test_online_manual_contract",
    "test_renderer_import",
    "test_ditto_service",
    "test_legacy_boundary",
)


def cases(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from cases(item)
        else:
            yield item


def worker(module, output):
    sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
    # Tests may use a local fixture HTTP server; real services are outside this entry.
    original_connect = socket.socket.connect

    def offline_connect(sock, address):
        if isinstance(address, tuple) and address[0] not in {"127.0.0.1", "localhost", "::1"}:
            raise RuntimeError("Offline regression attempted an external connection")
        return original_connect(sock, address)

    socket.socket.connect = offline_connect
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    started = time.monotonic()
    with (output / (module + ".log")).open("w", encoding="utf-8") as log:
        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            imported = importlib.import_module(module)
            loaded = unittest.defaultTestLoader.loadTestsFromModule(imported)
            suite = unittest.TestSuite(t for t in cases(loaded) if t.id().startswith(module + "."))
            if suite.countTestCases() == 0:
                raise ValueError(
                    "This module has no unittest cases; use its documented standalone entry"
                )
            result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    summary = {
        "module": module,
        "tests": result.testsRun,
        "failures": [test.id() for test, _ in result.failures],
        "errors": [test.id() for test, _ in result.errors],
        "skipped": len(result.skipped),
        "ok": result.wasSuccessful(),
        "seconds": round(time.monotonic() - started, 2),
    }
    (output / (module + ".json")).write_text(json.dumps(summary, indent=2) + "\n")
    return 0 if summary["ok"] else 1


def source_snapshot():
    paths = sorted((ROOT / "src").rglob("*.py"))
    paths += sorted((ROOT / "configs").glob("*.json"))
    paths += sorted((ROOT / "scripts").glob("*.py"))
    return {
        p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=("current", "historical", "all"), default="current")
    parser.add_argument(
        "--module", action="append", help="Run explicit module(s) instead of a suite"
    )
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument(
        "--timeout", type=float, default=180, help="Per test-module timeout in seconds"
    )
    parser.add_argument("--output", type=Path, default=ROOT / "out/repository-check")
    parser.add_argument("--worker", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.jobs < 1 or args.timeout <= 0:
        parser.error("jobs and timeout must be positive")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if args.worker:
        return worker(args.worker, output)
    available = sorted(p.stem for p in (ROOT / "scripts").glob("test_*.py"))
    historical = [name for name in available if name not in CURRENT]
    modules = (
        args.module or {"current": CURRENT, "historical": historical, "all": available}[args.suite]
    )

    def run(module):
        summary = output / (module + ".json")
        summary.unlink(missing_ok=True)
        command = [
            sys.executable,
            "-B",
            str(Path(__file__).resolve()),
            "--worker",
            module,
            "--output",
            str(output),
        ]
        with (output / (module + ".startup.log")).open("w", encoding="utf-8") as log:
            try:
                completed = subprocess.run(
                    command, cwd=ROOT, stdout=log, stderr=log, timeout=args.timeout
                )
            except subprocess.TimeoutExpired:
                return {"module": module, "ok": False, "status": "timeout"}
        if summary.exists():
            return json.loads(summary.read_text())
        return {
            "module": module,
            "ok": False,
            "status": "startup_error",
            "returncode": completed.returncode,
        }

    before = source_snapshot()
    results = []
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for row in pool.map(run, modules):
            results.append(row)
            print(
                f"{'PASS' if row['ok'] else 'FAIL'} {row['module']} ({row.get('tests', 0)} tests)",
                flush=True,
            )
    report = {
        "suite": args.suite,
        "modules": results,
        "tests": sum(row.get("tests", 0) for row in results),
        "ok": all(row["ok"] for row in results),
        "historical_modules": historical,
    }
    after = source_snapshot()
    report["source_files"] = after
    report["changed_during_checks"] = sorted(
        k for k in before.keys() | after.keys() if before.get(k) != after.get(k)
    )
    (output / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"{report['tests']} tests; report: {output / 'summary.json'}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
