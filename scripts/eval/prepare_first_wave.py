"""Prepare the approved retrospective first wave from an immutable deployment handoff."""
from __future__ import annotations

import argparse
import copy
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from evaluation.media import prepare
from evaluation.protocol import file_hash, freeze, read, require, validate_card, write


def item(id, text, *, mandatory=True, temporal=False, partial="仅在部分要求范围内成立；完全失效记 fail，证据不足记 unknown。"):
    return {"id": id, "text": text, "mandatory": mandatory, "temporal": temporal,
            "evidence": "sequence" if temporal else "frames", "partial_rule": partial}


def group(id, kind, *entries):
    return {"id": id, "kind": kind, "items": list(entries)}


def reviewed_card(task):
    """Source-only manual review; no output quality or desired ranking enters cards."""
    sid = task["source_id"]
    card = {k: task[k] for k in ("protocol", "task_id", "source_id", "track", "split", "source_video", "source_sha256",
                                "requirement", "duration_seconds", "source_start_seconds")}
    card.update(status="draft", style_required=True, creativity="open" if task["track"] == "short" else "bounded",
                annotation_note="Retrospective development evaluation. Source timeline reviewed before this scoring run; outputs already existed. Not a prospective held-out annotation.")
    if sid == "027":
        card.update(style_family="etching", scene_summary="俯瞰树木间的城镇屋顶，远处有圆顶、塔楼，天空明亮且基本空旷，视点缓慢移动。",
                    allowed_changes=["将颜色、材质、线条与明暗转为蚀刻版画语言；允许纸张质感和形体描绘的风格化简化。", "保留城镇和树木的主要布局、地标轮廓及原有视点变化；不无故增加新的独立主体。"])
        edits = [group("style_goal", "edit", item("etching_style", "整体呈现可辨认的十九世纪蚀刻版画风格。"))]
        if task["track"] == "long":
            edits += [group("ink_paper", "edit", item("black_ivory", "使用清晰黑墨和轻微做旧的象牙白纸底。"), item("monochrome", "将原有彩色转为单色明暗。")),
                      group("line_design", "edit", item("fine_contours", "用细轮廓线刻画屋顶、圆顶和塔楼。"), item("foliage_hatching", "树木阴影以密集交叉排线建立。")),
                      group("sky", "edit", item("unmarked_sky", "明亮天空大部分保持无刻线的留白，用于形成对比。"))]
        preservation = [group("layout", "preserve_core", item("town_layout", "保留城镇、前景屋顶、远处天际线与树丛的主要相对位置。"), item("landmarks", "原有显著圆顶与塔楼仍可对应，其基本轮廓及相对位置保持；允许线描简化。")),
                        group("camera", "preserve_core", item("camera_progression", "保持原片缓慢的视点移动方向及主要画面变化顺序。", temporal=True)),
                        group("incidental", "preserve_detail", item("roof_details", "可辨认的屋顶边缘和附属结构得到保留，允许线描概括。", mandatory=False), item("open_sky", "天空没有增加无关的独立物体或明显新主体；纸纹与排线属于允许表达。", mandatory=False))]
    elif sid == "024":
        card.update(style_family="digital_glitch", scene_summary="男子在米色皮质汽车后座持黑色手机贴耳通话，穿深色西装及白衬衫，头部、嘴部有细小动作。",
                    allowed_changes=["按要求让全画面呈现高反差、RGB 分离、像素横移、碎片方块和闪烁扫描线。", "允许有意的通道重影、局部位移及色彩高光变化；仍需辨认原男子、手机通话和车内关系。"])
        edits = [group("style_goal", "edit", item("glitch_style", "整段画面形成清晰可识别的数字故障艺术表达。")),
                 group("color", "edit", item("contrast", "阴影具有高对比，并有失真的彩色高光。"), item("rgb", "男子深色西装、座椅与车窗反射等处可见 RGB 通道分离。")),
                 group("spatial_glitches", "edit", item("horizontal_shifts", "画面存在水平像素位移。"), item("fragmented_blocks", "画面存在碎片块状故障效果。")),
                 group("scanlines", "edit", item("scanline_flicker", "扫描线纹理在全画面范围随时间闪烁。", temporal=True))]
        preservation = [group("subject_relation", "preserve_core", item("same_man", "男子仍是原来可辨认的人物；允许故障风格造成的通道重影，不将重影当成新增人物。"), item("phone_contact", "黑色手机、手与耳朵之间的通话关系仍清楚可辨。")),
                        group("event", "preserve_core", item("call_continues", "保持原有持续通话活动及主要动作进程；不要求消除用户指定的像素扰动。", temporal=True)),
                        group("layout", "preserve_detail", item("car_layout", "座椅、车窗和人物的主要空间关系保持，允许故障位移。", mandatory=False), item("fine_motion", "仍可对应原有细小头部、嘴部及手部运动顺序；不能由静态姿态推断。", mandatory=False, temporal=True))]
    elif sid == "fewshot_004":
        card.update(style_family="space_station_sports", scene_summary="两名前景球员隔着蓝色球桌对打，后方还有可见人物和球桌；球桌带弯曲支架，原场地有窗户、立柱和蓝色围挡。",
                    allowed_changes=["将环境改为金属墙面、蓝白光照和可透过大窗看到地球的太空站运动场馆。", "将球员衣服改成流线科幻运动服，并让球桌边缘发蓝光；保持人脸、运动、球路、球桌几何及镜头运动。", "背景表面和窗外景色可改变，保留明确要求的运动参与者与场景空间关系。"])
        edits = [group("arena", "edit", item("space_arena", "室内成为可识别的未来太空站运动场馆，具有金属墙面。"), item("blue_white_lighting", "场馆具有蓝白色照明。"), item("earth_windows", "通过较大窗户能辨认地球景象。")),
                 group("clothing", "edit", item("scifi_suits", "可见球员穿着流线科幻运动服。")),
                 group("table_light", "edit", item("blue_edges", "球桌边缘出现蓝色发光；台面／台面外沿属于球桌边缘，仅下方支架发光不足以完整满足该项。", partial="仅部分桌沿发光，或蓝光主要落在下方支架而非桌沿，记 partial；完全没有蓝色发光记 fail。"))]
        preservation = [group("players", "preserve_core", item("faces", "原有可辨认球员脸部及身份特征保持，允许衣服变化。"), item("player_roles", "保留前景两人的左右位置和对打关系；背景可见人物不被无故增删，正常遮挡不算删除。")),
                        group("geometry", "preserve_core", item("table_geometry", "保持台面外形、透视和弯曲支架等原有球桌几何结构，允许表面和光照改变。"), item("net", "球网的位置、走向和基本形状保持。")),
                        group("performance", "preserve_core", item("playing_motion", "挥拍及击球动作的主要顺序、方向与节奏保持。", temporal=True), item("ball_trajectory", "可观察球体的运动路径、反弹与接触时序保持；看不清小球时记 unknown。", temporal=True), item("camera_motion", "镜头取景及运动顺序保持。", temporal=True)),
                        group("incidental", "preserve_detail", item("table_markings", "台面和球网的可辨细部、标线关系保持，允许表面处理改变。", mandatory=False))]
    else:
        raise ValueError(sid)
    card["groups"] = edits + preservation
    return freeze(card, "source-review-by-evaluation-session-2026-10-30")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--handoff", type=Path, required=True)
    p.add_argument("--run", type=Path, required=True)
    args = p.parse_args()
    args.run.mkdir(parents=True, exist_ok=True)
    tasks = read(args.handoff / "tasks.json")
    cards = {}
    for task in tasks:
        path = args.run / "cards" / (task["task_id"] + ".json")
        card = validate_card(read(ROOT / task["card"])) if task["card"] else reviewed_card(task)
        if path.exists():
            require(read(path) == card, "Existing first-wave card differs; create a new run")
        else:
            write(path, card)
        cards[task["task_id"]] = path
    rows = read(args.handoff / "baseline-planner.manifest.template.json")["cases"]
    manifest = []
    for row in rows:
        row = dict(row)
        key = Path(row["card"]).name.replace(".card.json", "")
        if key in {"041_short", "041_long"}:
            key = key.replace("_", "__", 1)
        row["card"] = str(cards[key].relative_to(ROOT)) if cards[key].is_absolute() else str(cards[key])
        manifest.append(row)
    primary_ids = []
    goal = {"041": "short", "027": "short", "024": "long", "fewshot_004": "long"}
    for row in manifest:
        card = read(ROOT / row["card"])
        direct = row["case_id"].endswith("__" + goal[card["source_id"]]) and "__baseline__" in row["case_id"]
        if "__planner__" in row["case_id"] or direct:
            primary_ids.append(row["case_id"])
    for sid, track in goal.items():
        card_path = cards[f"{sid}__{track}"]
        card = read(card_path)
        manifest.append({"case_id": "source_control__" + sid, "method": "source_control", "seed": 42,
                         "card": str(card_path), "output_video": card["source_video"]})
    write(args.run / "manifest.json", {"cases": manifest})
    write(args.run / "primary_cases.json", primary_ids)
    write(args.run / "run_plan.json", {"protocol": "lha-evaluation-v1", "handoff": str(args.handoff),
          "status": "prepared", "judge_model": "gpt-6.1-sol", "reasoning_effort": "xhigh",
          "generated_outputs": 28, "source_controls": 4, "primary_pairs": 8,
          "scope": "Retrospective development evaluation. Independent blind judge; process records excluded.",
          "evidence": "Native frame PTS/root mappings. Full dense interval for semantic and temporal evaluation; no endpoint repetition.",
          "cards": {key: read(path)["card_sha256"] for key, path in cards.items()}})
    # Prepare all evidence before freezing reference sets; resume exactly, no judge calls here.
    for row in manifest:
        card = read(ROOT / row["card"])
        dest = args.run / "evidence" / row["case_id"]
        if (dest / "evidence.json").exists():
            evidence = read(dest / "evidence.json")
            require(evidence["card_sha256"] == card["card_sha256"] and evidence["output_sha256"] == file_hash(ROOT / row["output_video"]), "Existing evidence changed")
        else:
            evidence = prepare(card, ROOT / row["output_video"], dest, root=ROOT,
                               dense_ranges=[[0, card["duration_seconds"]]], mapping=read(ROOT / row["mapping"]) if row.get("mapping") else None)
        print("prepared", row["case_id"], len(evidence["pairs"]), flush=True)
    for key in cards:
        candidates = []
        for row in manifest:
            if row["method"] == "source_control" or read(ROOT / row["card"])["task_id"] != key:
                continue
            e = read(args.run / "evidence" / row["case_id"] / "evidence.json")
            ix = sorted({0, len(e["output_images"]) // 2, len(e["output_images"]) - 1})
            images = [e["output_images"][i] for i in ix]
            candidates.append({"images": images, "image_sha256": [file_hash(p) for p in images]})
        # Reference pool ordering is independent of method names and output scores.
        candidates.sort(key=lambda c: c["image_sha256"][0])
        write(args.run / "references" / (key + ".json"), {"task_id": key, "candidates": candidates})
    print("First-wave materials complete:", len(manifest), "cases", flush=True)


if __name__ == "__main__":
    main()
