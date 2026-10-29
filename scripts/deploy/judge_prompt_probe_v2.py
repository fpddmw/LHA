"""Evaluate both generators with atomic criteria and the actual source-frame mapping.

This creates separate v2 judgments; historical Bernini judgments remain intact.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from run_prompt_probe import digest, save

PROTOCOL = "atomic-native-aligned-v3"
PRESERVE = {
    "027": [
        "建筑数量和整体天际线布局", "屋顶、圆顶和塔楼的具体轮廓与相对位置",
        "树丛的位置和占据范围", "天空中没有新增独立物体", "镜头取景与可见的运动趋势",
    ],
    "041": [
        "原来的两个人及各自身份特征（允许绘本化简化）", "两人的相对位置",
        "男子继续进行书写动作", "书写工具的类别与可辨认形态",
        "笔记本的装订和页本结构", "独立纸张与笔记本仍是两个可区分对象",
        "女子与男子肩部的接触关系", "手、纸本和桌面的空间关系",
        "镜头取景与可见的运动趋势",
    ],
    "fewshot_004": [
        "原来的两名球员及各自身份特征", "球员的左右位置与角色",
        "可观察的挥拍动作顺序", "可见球体数量，没有新增独立球体",
        "球路与击球时刻", "球桌桌面的几何形状和透视", "球网的位置和形状",
        "镜头取景与可见的运动趋势",
    ],
    "024": [
        "原男子可辨认的身份特征", "持续进行通话的动作",
        "手机与耳朵、手之间的接触关系", "头部运动顺序", "嘴部运动顺序",
        "手部运动顺序", "车座、车窗和人物的空间布局", "镜头取景与可见的运动趋势",
    ],
}
SYSTEM = """Compare source and edited video frames. The first image group is SOURCE,
the second is OUTPUT. The request includes exact frame correspondence. Assess the user
requirement, not a planner. The generator name, prompt condition and prior scores are hidden.
Write all evidence and summaries in Chinese; keep the requested JSON keys/labels unchanged.
Separate requested appearance changes from semantic changes. Etching or illustration can
change texture, color and realistic facial rendering; judge identity using observable stable
features under that allowed change. Glitch art intentionally shifts pixels and can flicker.
Do not penalize intended visual effects merely as artifacts. Report only visible evidence.
Writing action, writing implement, notebook structure and loose paper are independent items.
You only see 12 aligned samples per clip. Exact fast ball paths, contact times, fine mouth/hand
motion and between-frame continuity generally require denser evidence: use unjudgeable when
these images do not establish the claim. Do not infer full temporal preservation from poses.
For a short style-only request, detailed rendering cues are descriptive, not automatically
mandatory. Copy every observation item exactly once, including unjudgeable items.
Return JSON: style_match {label: clear|partial|absent|unjudgeable, evidence},
edits [{item, explicitly_required: boolean, label: done|partial|not_done|unjudgeable,
evidence, times_seconds: [output times], confidence: high|medium|low}],
preservation [{item, label: kept|partial|changed|unjudgeable, evidence,
times_seconds: [output times], confidence: high|medium|low}],
unintended_damage: [strings], temporal_limitations: [strings], summary: string.
Do not combine item labels into a total score, infer generator identity, or recommend code edits.
"""


def decode(path):
    import av
    with av.open(str(path)) as container:
        return [(float(f.time), f.to_image()) for f in container.decode(video=0)]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--mapping-manifest", type=Path, required=True)
    p.add_argument("--only", nargs="*")
    p.add_argument("--prepare-only", action="store_true")
    args = p.parse_args()
    manifest = args.manifest.resolve()
    spec = json.loads(manifest.read_text(encoding="utf-8"))
    mapped = {c["case_id"]: c for c in json.loads(args.mapping_manifest.read_text(encoding="utf-8"))["cases"]}
    samples = {s["sample_id"]: s for s in json.loads((ROOT / "benchmark_data/all_samples.json").read_text(encoding="utf-8"))}
    model = None
    for case in spec["cases"]:
        if args.only and case["case_id"] not in args.only:
            continue
        directory = manifest.parent / case["case_id"]
        result_path = directory / "result.json"
        if not result_path.exists():
            continue
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if result.get("status") != "complete":
            continue
        mapping = mapped[case["case_id"]]
        for key in ("prompt", "source_video_sha256", "num_frames", "delivery_frames", "fps", "seed"):
            assert case[key] == mapping[key], (case["case_id"], key)
        source_path, output_path = ROOT / case["source_video"], directory / "edited.mp4"
        assert digest(source_path) == case["source_video_sha256"]
        assert digest(output_path) == result["output_sha256"]
        sample = samples[case["sample_id"]]
        requirement = sample["prompt_short"] if case["condition"] == "short" else sample["prompt_long"]
        source, output = decode(source_path), decode(output_path)
        native = decode(directory / "native.mp4")
        assert len(output) == case["delivery_frames"] and len(native) == case["num_frames"]
        # A packet-copy trim can omit a B-frame near the end rather than the last
        # display frame. Resolve each delivered frame by PTS, then verify pixels.
        native_indices = [round((t - native[0][0]) * case["fps"]) for t, _ in output]
        assert all(0 <= i < len(native) for i in native_indices)
        protocol_input = {"protocol": PROTOCOL, "system": SYSTEM, "user_requirement": requirement,
                          "style_observations": case["evaluation"]["style"],
                          "preserve_observations": PRESERVE[case["sample_id"]],
                          "mapping": mapping["conditioning_source_indices"],
                          "delivery_native_indices": native_indices,
                          "source_sha256": case["source_video_sha256"], "output_sha256": result["output_sha256"]}
        signature = hashlib.sha256(json.dumps(protocol_input, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        target = directory / "judgment_v3.json"
        if target.exists():
            assert json.loads(target.read_text(encoding="utf-8"))["signature"] == signature, "Stale v3 judgment"
            print(json.dumps({"reuse": case["case_id"], "protocol": PROTOCOL}), flush=True)
            continue
        raw_path = directory / "judge_raw_v3.json"
        prior_raw = None
        if raw_path.exists():
            provenance = json.loads((directory / "judge_provenance_v3.json").read_text(encoding="utf-8"))
            assert provenance["signature"] == signature, "Raw judgment belongs to different inputs"
            prior_raw = json.loads(raw_path.read_text(encoding="utf-8"))
        indices = sorted({round(i * (len(output)-1) / 11) for i in range(12)})
        pairs, source_images, output_images = [], [], []
        frames_dir = directory / "judge_v3_frames"
        frames_dir.mkdir(exist_ok=True)
        for out_index in indices:
            native_index = native_indices[out_index]
            assert native[native_index][1].tobytes() == output[out_index][1].tobytes(), "Delivery frame differs from native frame"
            source_index = mapping["conditioning_source_indices"][native_index]
            st, si = source[source_index]
            ot, oi = output[out_index]
            sp, op = frames_dir / f"source_{source_index:04d}.jpg", frames_dir / f"output_{out_index:04d}.jpg"
            si.save(sp, quality=95)
            oi.save(op, quality=95)
            source_images.append(str(sp)); output_images.append(str(op))
            pairs.append({"source_index": source_index, "output_index": out_index, "native_index": native_index,
                          "source_seconds": round(st, 6), "output_seconds": round(ot, 6)})
        request = {"user_requirement": requirement, "source_images_first": len(source_images),
                   "frame_correspondence": pairs, "style_observations": case["evaluation"]["style"],
                   "preserve_observations": PRESERVE[case["sample_id"]]}
        save(directory / "judge_input_v3.json", request)
        save(directory / "judge_provenance_v3.json", {"signature": signature, **protocol_input,
                                                      "frame_correspondence": pairs})
        if args.prepare_only:
            print(json.dumps({"prepared": case["case_id"], "pairs": len(pairs)}), flush=True)
            continue
        if model is None:
            from vlm.codex_vlm import CodexVisionModel
            model = CodexVisionModel(role="probe_evaluator")
        os.environ["LOW_HIGH_VLM_AUDIT_LOG"] = str(manifest.parent / "judge_calls_v3.jsonl")
        if prior_raw is not None:
            response = prior_raw
        else:
            response = model.predict_json(system_prompt=SYSTEM, user_text=json.dumps(request, ensure_ascii=False),
                                          image_paths=source_images + output_images)
            save(raw_path, response)
        expected = {"edits": case["evaluation"]["style"], "preservation": PRESERVE[case["sample_id"]]}
        for key, items in expected.items():
            supplied = response[key]
            for item in items:
                assert sum(row["item"] == item for row in supplied) == 1, (case["case_id"], key, item)
            extras = [row for row in supplied if row["item"] not in items]
            if extras:
                response.setdefault("additional_observations", {})[key] = extras
            response[key] = [next(row for row in supplied if row["item"] == item) for item in items]
        valid = {"edits": {"done", "partial", "not_done", "unjudgeable"},
                 "preservation": {"kept", "partial", "changed", "unjudgeable"}}
        for key, labels in valid.items():
            for row in response[key]:
                assert row["label"] in labels
        save(target, {"case_id": case["case_id"], "protocol": PROTOCOL, "signature": signature,
                      "output_sha256": result["output_sha256"], "model": model.model,
                      "reasoning_effort": model.reasoning_effort,
                      "evidence_scope": "12 source-aligned sampled frames per clip; not full motion verification",
                      "judgment": response})
        print(json.dumps({"complete": case["case_id"], "style": response["style_match"]["label"]}), flush=True)


if __name__ == "__main__":
    main()
