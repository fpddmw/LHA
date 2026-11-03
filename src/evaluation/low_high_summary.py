"""Source-macro statistics with explicit planned/missing denominators."""
from collections import defaultdict, Counter
from statistics import mean
from critic_harness.one_shot import DIMENSIONS
from .low_high import PROTOCOL
from .registry import LOW_HIGH_METRICS, validate_low_high_rating
from .final_suite import ratings


def summarize(rows):
    """Rows: source_id, length(short/long), judge, variant, result(or null)."""
    grouped = defaultdict(list)
    profiles = set()
    seen = set()
    for row in rows:
        if row.get("length") not in {"short","long"} or any(not row.get(k) for k in ("source_id","judge","variant","sample_id")):
            raise ValueError("Each planned row needs source_id, sample_id, length, judge and variant")
        key=tuple(row[k] for k in ("source_id","sample_id","length","judge","variant"))
        if key in seen: raise ValueError("Duplicate planned sample")
        seen.add(key)
        result=row.get("result")
        if result and result.get("report"):
            if result.get("model")!=row["judge"] or result["report"].get("protocol_id")!=PROTOCOL:
                raise ValueError("Wrong judge or historical rubric in low-high summary")
            if not result.get("profile_sha256"): raise ValueError("Missing frozen evaluation profile")
            profiles.add(result["profile_sha256"])
        for scope in (row["length"],"all"):
            grouped[(row["judge"],row["variant"],scope)].append(row)
    if len(profiles)>1: raise ValueError("Do not aggregate different frozen evaluation protocols")
    output={"protocol_id":PROTOCOL,"profile_sha256":next(iter(profiles),None),"weighting":"mean within source, then mean across sources","groups":[]}
    for (judge,variant,scope),group in sorted(grouped.items()):
        columns={}
        for dimension,spec in LOW_HIGH_METRICS.items():
            sources=defaultdict(list)
            counts={s:0 for s in ("scored","unknown","not_assessed","not_applicable","missing","not_measured","execution_failed")}
            for row in group:
                result=row.get("result")
                report=result.get("report") if result else None
                rating=ratings(result).get(dimension)
                if rating is None and spec["track"] in {"short","long"} and spec["track"]!=row["length"]:
                    rating={"status":"not_applicable","score":None}
                status=rating["status"] if rating else "missing"
                counts[status]=counts.get(status,0)+1
                if status=="scored":
                    score=rating["score"]
                    if spec["unit"]=="ordinal": validate_low_high_rating(score)
                    sources[row["source_id"]].append(score)
                elif rating and rating["score"] is not None: raise ValueError("Unassessed scores must be null")
            columns[dimension]={"unit":spec["unit"],"scale":spec["scale"],"planned":len(group),"valid":counts["scored"],"statuses":counts,
                "planned_sources":len({r["source_id"] for r in group}),"valid_sources":len(sources),
                "mean_source_macro":mean(mean(v) for v in sources.values()) if sources else None,
                "mean_micro":mean(x for v in sources.values() for x in v) if sources else None}
        output["groups"].append({"judge":judge,"variant":variant,"length":scope,"dimensions":columns})
    return output


def paired(rows):
    """Rows of planned before/after results. Separate judges and short/long groups."""
    groups=defaultdict(list)
    seen=set()
    for row in rows:
        if not row.get("sample_id"):
            raise ValueError("Paired rows require the planned sample_id")
        identity=tuple(row.get(k) for k in ("source_id","sample_id","length","judge"))
        if identity in seen: raise ValueError("Duplicate planned paired sample")
        seen.add(identity)
        before,after=row.get("before"),row.get("after")
        for result in (before,after):
            if ratings(result) and any(not result.get(k) for k in ("source_sha256","plan_sha256","profile_sha256")):
                raise ValueError("Scored paired results need source, task and profile bindings")
        if before and after:
            for key in ("source_sha256","plan_sha256"):
                if before.get(key) is not None and after.get(key) is not None and before[key] != after[key]:
                    raise ValueError("Paired samples must share source and task interpretation")
        if row.get("length") not in {"short","long"} or not row.get("source_id") or not row.get("judge"):
            raise ValueError("Paired rows need source, judge and short/long")
        for scope in (row["length"],"all"): groups[(row["judge"],scope)].append(row)
    output=[]
    for (judge,scope),group in sorted(groups.items()):
        columns={}
        for dim,spec in LOW_HIGH_METRICS.items():
            sources=defaultdict(list); profiles=set()
            for row in group:
                values=[]
                for side in ("before","after"):
                    result=row.get(side)
                    if result:
                        if result.get("report") and (result.get("model")!=judge or result["report"].get("protocol_id")!=PROTOCOL or not result.get("profile_sha256")):
                            raise ValueError("Invalid paired judge/protocol identity")
                        if result.get("profile_sha256"):profiles.add(result["profile_sha256"])
                        rating=ratings(result).get(dim)
                        if rating and rating["status"]=="scored":
                            if spec["unit"]=="ordinal": validate_low_high_rating(rating["score"])
                            values.append(rating["score"])
                if len(values)==2: sources[row["source_id"]].append(values[1]-values[0])
            if len(profiles)>1: raise ValueError("Paired protocol mismatch")
            deltas=[v for values in sources.values() for v in values]
            oriented=[-v if spec["direction"]=="lower" else v for v in deltas]
            columns[dim]={"unit":spec["unit"],"planned":len(group),"valid":len(deltas),"missing":len(group)-len(deltas),
                "planned_sources":len({r["source_id"] for r in group}),"valid_sources":len(sources),
                "mean_delta_source_macro":mean(mean(v) for v in sources.values()) if sources else None,
                "improved":sum(v>0 for v in oriented) if spec["direction"]!="context" else None,"tied":sum(v==0 for v in deltas),"worsened":sum(v<0 for v in oriented) if spec["direction"]!="context" else None}
        output.append({"judge":judge,"length":scope,"dimensions":columns})
    return output
