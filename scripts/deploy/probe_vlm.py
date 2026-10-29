"""Exercise both hosted roles using actual frames before GPU generation."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from vlm import extract_frames, resolve_vision_model

if __name__ == "__main__":
    frames = extract_frames(str(ROOT / "smoke-data" / "2_low-cost.mp4"), max_frames=2)
    if len(frames) != 2:
        raise RuntimeError("Could not decode the two input frames")
    for role in ("planner", "critic"):
        response = resolve_vision_model(role).predict_json(
            system_prompt='Describe only the visible images. Return a JSON object with keys "scene", "people", "changes".',
            user_text="These are two frames from one video. Describe the scene, visible people, and differences. No tools.",
            image_paths=frames,
        )
        if not response.get("scene"):
            raise RuntimeError(f"{role}: empty visual description")
        print(json.dumps({"role": role, "response": response}, ensure_ascii=False), flush=True)
