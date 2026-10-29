"""Check real run artifacts, decoded video, both model roles, and memory updates."""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import subprocess


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def verify(root: Path) -> dict:
    loop = root / "loop"
    result = read(loop / "loop.result.json")
    if result.get("status") not in {"accepted", "max_attempts_reached"}:
        raise RuntimeError("Loop did not complete")
    attempts = read(loop / "loop.trace.json")["attempts"]
    if not attempts:
        raise RuntimeError("No completed attempts")
    videos = []
    for attempt in attempts:
        directory = loop / f"attempt_{attempt['attempt_index']:03d}"
        plan = read(directory / "planner.response.json")
        edit = read(directory / "edit.response.json")
        evaluation = read(directory / "evaluation.response.json")
        reflection = read(directory / "reflection.response.json")
        read(directory / "memory.contract.json")
        read(directory / "memory.analysis.json")
        if not plan.get("compiled_edit_prompt"):
            raise RuntimeError("Planner has no executable edit prompt")
        if edit.get("backend") != "bernini":
            raise RuntimeError("Run did not use Bernini")
        if evaluation.get("evaluation_incomplete") or not evaluation.get("raw_vlm_response"):
            raise RuntimeError("Critic evaluation is incomplete")
        scores = evaluation.get("scores", {})
        if len(scores) != 8 or not all(isinstance(v, (int, float)) and math.isfinite(v) and 0 <= v <= 1 for v in scores.values()):
            raise RuntimeError("Critic scores are missing or invalid")
        if reflection.get("action") not in {"accept", "local_refine_prompt", "global_replan"}:
            raise RuntimeError("Invalid reflection action")
        video = directory / "edited.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-f", "null", "-"], check=True, capture_output=True)
        probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,nb_frames,avg_frame_rate", "-of", "json", str(video)],
            check=True, capture_output=True, text=True)
        metadata = json.loads(probe.stdout)["streams"][0]
        if int(metadata["nb_frames"]) < 2:
            raise RuntimeError("Output has fewer than two frames")
        videos.append({"path": str(video), **metadata, "score": scores["overall_score"], "action": reflection["action"]})
    memory = read(root / "memory.json")
    for key in ["run_records", "evaluation_records", "evolution_records"]:
        if len(memory[key]) < len(attempts):
            raise RuntimeError(f"Missing memory updates: {key}")
    calls = [json.loads(line) for line in (root / "vlm-calls.jsonl").read_text().splitlines() if line.strip()]
    for role in ["planner", "critic"]:
        evidence = [c for c in calls if c.get("role") == role and c.get("images", 0) > 0]
        if not evidence or any(c.get("model") != "gpt-6.1-sol" or c.get("reasoning_effort") != "xhigh" for c in evidence):
            raise RuntimeError(f"Missing GPT-6.1-sol xhigh vision evidence for {role}")
    return {"workflow_verified": True, "loop_status": result["status"],
        "attempts": len(attempts), "videos": videos,
        "model_calls": len(calls), "roles": sorted({c["role"] for c in calls}),
        "memory_records": {k: len(memory[k]) for k in ["run_records", "evaluation_records", "evolution_records"]}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    report = verify(args.run_dir.resolve())
    (args.run_dir / "verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
