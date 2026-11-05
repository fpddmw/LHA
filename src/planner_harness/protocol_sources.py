"""Reviewed execution dependencies; broad audit inventories live outside cohort identity.

Add a dependency here when the current creative path starts executing it. Model-visible
knowledge/manuals are additionally enumerated by CreativeKnowledge, including assets.
"""

from pathlib import Path
from functools import lru_cache

from .common import sha

MODULES = {
    "planner_harness": "__init__ common lock runner video event_observation knowledge knowledge_search creative_knowledge creative creative_actions tool_interface candidate_view candidate_selection context working_memory resources accounting supervisor owned_process recovery integrity json_output model_call report_call execution automatic_review continuation delivery delivery_review experience_usage creative_report report protocol_sources lineage resumption upgrade",
    "critic_harness": "__init__ adapter one_shot qualitative",
    "server_runtime": "__init__ queue engine service renderers ditto media_cache lifecycle",
    "vlm": "__init__ openrouter litellm_vlm settings chatgpt_subscription chatgpt_auth chatgpt_relay responses_stream",
    "experiments": "__init__ creative_benchmark unified_benchmark pe_loop bernini_pe render_profiles device_scheduler results preflight recovery resumption",
}
SCRIPTS = (
    "scripts/benchmark_device_worker.py",
    "scripts/run_server_pipeline.py",
    "scripts/prepare_creative_smoke.py",
    "scripts/run_creative_benchmark.py",
    "scripts/creative_benchmark_schedule.py",
    "scripts/run_creative_judge.py",
    "scripts/run_low_high_eval.py",
    "scripts/benchmark_results.py",
    "scripts/accounting_worker.py",
    "scripts/run_bernini_benchmark.py",
    "scripts/run_planner_worker.py",
    "scripts/deploy/run_prompt_probe.py",
    "configs/creative-loop-v1.json",
)


def protocol_inventory(root):
    return dict(_protocol_inventory(str(Path(root).resolve())))


@lru_cache(maxsize=8)
def _protocol_inventory(root):
    root = Path(root)
    names = [
        f"src/{package}/{module}.py"
        for package, modules in MODULES.items()
        for module in modules.split()
    ]
    names.extend(
        name
        for name in SCRIPTS
        if name
        not in {
            "scripts/run_creative_judge.py",
            "scripts/run_low_high_eval.py",
            "scripts/benchmark_results.py",
            "scripts/creative_benchmark_schedule.py",
        }
    )
    return {name: sha(root / name) for name in sorted(names)}


def audit_inventory(root):
    root = Path(root)
    return {
        p.relative_to(root).as_posix(): sha(p)
        for p in sorted((root / "src").rglob("*"))
        if p.is_file() and p.suffix in {".py", ".md"}
    }
