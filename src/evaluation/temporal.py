"""Raw temporal diagnostics. No conversion to ordinal VLM scores."""
from __future__ import annotations

import math
from statistics import mean

from .media import decode
from .protocol import file_hash

PROTOCOL = "lha-low-high-temporal-v1"
FLOW = {"method":"opencv-farneback", "pyr_scale":0.5,"levels":3,"winsize":15,
        "iterations":3,"poly_n":5,"poly_sigma":1.2,"flags":0}


def _arrays(decoded, max_side):
    import cv2
    import numpy as np
    if type(max_side) is not int or max_side < 32:
        raise ValueError("max_side must be at least 32")
    result = []
    size = decoded["frames"][0].size
    scale = min(1,max_side/max(size))
    target = tuple(max(1,round(v*scale)) for v in size)
    for image in decoded["frames"]:
        if image.size != size:
            raise ValueError("Variable image dimensions require explicit registration")
        result.append(cv2.resize(np.asarray(image.convert("RGB")),target,interpolation=cv2.INTER_AREA))
    return result


def _flow(a,b):
    import cv2
    return cv2.calcOpticalFlowFarneback(cv2.cvtColor(a,cv2.COLOR_RGB2GRAY),cv2.cvtColor(b,cv2.COLOR_RGB2GRAY),None,
                                      **{k:v for k,v in FLOW.items() if k != "method"})


def _pair(a,b):
    import cv2
    import numpy as np
    forward,backward = _flow(a,b),_flow(b,a)
    h,w = a.shape[:2]
    x,y = np.meshgrid(np.arange(w,dtype=np.float32),np.arange(h,dtype=np.float32))
    mx,my = x+forward[:,:,0], y+forward[:,:,1]
    back = cv2.remap(backward,mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
    confidence = np.linalg.norm(forward+back,axis=2) <= 1.0 + 0.05*np.linalg.norm(forward,axis=2)
    mask = (mx>=0)&(mx<=w-1)&(my>=0)&(my<=h-1)&confidence
    warped = cv2.remap(b,mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
    error = np.abs(a.astype(np.float32)-warped.astype(np.float32)).mean(axis=2)/255.0
    return forward,mask,error


def _compute(output, *, source=None, motion_scope=None, geometry_aligned=False,
            cut_times=(), max_side=512, freeze_threshold=0.001, min_valid_fraction=0.1):
    import cv2
    import numpy as np
    if not math.isfinite(freeze_threshold) or freeze_threshold < 0 or not 0 < min_valid_fraction <= 1:
        raise ValueError("Invalid diagnostic thresholds")
    if any(type(t) not in (int,float) or not math.isfinite(t) or t < 0 for t in cut_times):
        raise ValueError("Declared cut times must be finite nonnegative source times")
    decoded = decode(output)
    images = _arrays(decoded,max_side)
    times = decoded["times"]
    diagonal = math.hypot(images[0].shape[1],images[0].shape[0])
    pairs = []
    for index,(a,b) in enumerate(zip(images,images[1:])):
        dt = times[index+1]-times[index]
        row = {"indices":[index,index+1],"times":[times[index],times[index+1]]}
        if any(times[index] < t <= times[index+1] for t in cut_times):
            pairs.append({**row,"status":"declared_cut","warp_error":None,"motion_per_second":None})
            continue
        flow,mask,error = _pair(a,b)
        coverage = float(mask.mean())
        valid = coverage >= min_valid_fraction
        pairs.append({**row,"status":"scored" if valid else "unknown","valid_pixel_fraction":coverage,
            "warp_error":float(error[mask].mean()) if valid else None,
            "motion_per_second":float(np.linalg.norm(flow,axis=2)[mask].mean()/diagonal/dt) if valid else None})
    valid = [row for row in pairs if row["status"] == "scored"]
    duration = sum(row["times"][1]-row["times"][0] for row in valid)
    def weighted(key):
        return sum(row[key]*(row["times"][1]-row["times"][0]) for row in valid)/duration if duration else None
    result = {"protocol_id":PROTOCOL,"output_sha256":file_hash(output),"flow":FLOW,"opencv_version":cv2.__version__,
        "analysis_size":[images[0].shape[1],images[0].shape[0]],"max_side":max_side,
        "mask":"in-bounds and forward/backward residual <= 1px + .05*forward magnitude",
        "declared_cut_times":list(cut_times),"min_valid_pixel_fraction":min_valid_fraction,
        "planned_pairs":len(pairs),"valid_pairs":len(valid),"declared_cut_pairs":sum(r["status"]=="declared_cut" for r in pairs),
        "unknown_pairs":sum(r["status"]=="unknown" for r in pairs),"valid_seconds":duration,
        "flow_warp_l1":weighted("warp_error"),"motion_diagonals_per_second":weighted("motion_per_second"),
        "freeze_threshold_diagonals_per_second":freeze_threshold,
        "low_motion_duration_fraction":sum((r["times"][1]-r["times"][0]) for r in valid if r["motion_per_second"] < freeze_threshold)/duration if duration else None,
        "pairs":pairs,"limitations":["Farneback is an estimated optical-flow diagnostic, not a semantic motion judge.",
            "Low motion may be intentional. Interpret freeze alongside task requirements and source motion.",
            "Warp error measures flow-compensated change; it does not establish semantic event correctness."]}
    scope = motion_scope or {"required":False,"reason":"No frozen retained-motion scope supplied","regions":[]}
    if not scope.get("required"):
        result["source_motion"] = {"status":"not_applicable","reason":scope.get("reason","Motion reinterpretation allowed")}
    elif not source or not geometry_aligned or not scope.get("regions"):
        result["source_motion"] = {"status":"unknown","reason":"Retained motion needs source, declared corresponding regions and verified pixel geometry"}
    else:
        result["source_motion"] = _source_motion(source,output,decoded,images,scope,cut_times,max_side,min_valid_fraction)
    return result


def _source_motion(source,output,out,images,scope,cuts,max_side,min_valid):
    import numpy as np
    src = decode(source)
    source_images = _arrays(src,max_side)
    if source_images[0].shape != images[0].shape:
        return {"status":"unknown","reason":"Source/output geometry differs; register before comparison"}
    h,w = images[0].shape[:2]
    region = np.zeros((h,w),dtype=bool)
    for r in scope["regions"]:
        if len(r)!=4 or not all(math.isfinite(v) for v in r) or not 0<=r[0]<r[2]<=1 or not 0<=r[1]<r[3]<=1:
            raise ValueError("Invalid frozen motion region")
        region[int(r[1]*h):max(int(r[1]*h)+1,int(r[3]*h)),int(r[0]*w):max(int(r[0]*w)+1,int(r[2]*w))] = True
    rows=[]
    for i,(a,b) in enumerate(zip(source_images,source_images[1:])):
        t0,t1=src["times"][i:i+2]
        if any(t0<t<=t1 for t in cuts):
            rows.append({"source_indices":[i,i+1],"status":"declared_cut"}); continue
        selected=[min(range(len(out["times"])),key=lambda k:abs(out["times"][k]-t)) for t in (t0,t1)]
        if selected[0]==selected[1] or any(abs(out["times"][k]-t)>out["step"]/2+1e-6 for k,t in zip(selected,(t0,t1))):
            rows.append({"source_indices":[i,i+1],"status":"unknown","reason":"No distinct PTS-aligned frame pair"}); continue
        sf,sm,_=_pair(a,b)
        of,om,_=_pair(images[selected[0]],images[selected[1]])
        mask=region&sm&om
        coverage=float(mask.sum()/region.sum())
        if coverage<min_valid:
            rows.append({"source_indices":[i,i+1],"status":"unknown","valid_region_fraction":coverage});continue
        diagonal=math.hypot(w,h)
        sv=sf/(t1-t0)/diagonal
        ov=of/(out["times"][selected[1]]-out["times"][selected[0]])/diagonal
        rows.append({"source_indices":[i,i+1],"output_indices":selected,"status":"scored","valid_region_fraction":coverage,
            "source_times":[t0,t1],"output_times":[out["times"][k] for k in selected],
            "flow_velocity_error":float(np.linalg.norm(sv-ov,axis=2)[mask].mean()),
            "source_motion":float(np.linalg.norm(sv,axis=2)[mask].mean()),"output_motion":float(np.linalg.norm(ov,axis=2)[mask].mean())})
    valid=[r for r in rows if r["status"]=="scored"]
    return {"status":"scored" if valid else "unknown","source_sha256":file_hash(source),"output_sha256":file_hash(output),
            "scope":scope,"time_mapping":"identity seconds, nearest native PTS within half median output frame interval",
            "units":"image diagonals per second","planned_pairs":len(rows),"valid_pairs":len(valid),
            "flow_velocity_error":mean(r["flow_velocity_error"] for r in valid) if valid else None,"pairs":rows}


def trajectory_error(source_points,output_points,*,required=False,confidence=0.5):
    """Optional supplied, registered tracks; no pose detector is implied.

    Each point has id,time,x,y,confidence. Coordinates share a normalized registered
    image plane and time is the common source timeline. Report observed coverage.
    """
    if not required:
        return {"status":"not_applicable","reason":"Exact trajectory retention is outside task scope"}
    if not math.isfinite(confidence) or not 0 <= confidence <= 1:
        raise ValueError("Track confidence threshold must be between 0 and 1")
    def index(points):
        result={}
        for p in points:
            if not isinstance(p.get("id"),str) or not p["id"] or any(type(p.get(k)) not in (int,float) or not math.isfinite(p[k]) for k in ("time","x","y","confidence")) or p["time"]<0 or not 0<=p["confidence"]<=1 or not 0<=p["x"]<=1 or not 0<=p["y"]<=1:
                raise ValueError("Tracks require normalized registered coordinates and finite confidence/times")
            key=(p["id"],p["time"])
            if key in result: raise ValueError("Duplicate track identity/time")
            result[key]=p
        return result
    src,out=index(source_points),index(output_points)
    errors=[math.hypot(p["x"]-out[k]["x"],p["y"]-out[k]["y"])/math.sqrt(2) for k,p in src.items()
            if k in out and min(p["confidence"],out[k]["confidence"])>=confidence]
    return {"status":"scored" if errors else "unknown","planned_points":len(src),"valid_points":len(errors),
            "mean_position_error_diagonals":mean(errors) if errors else None,"confidence_threshold":confidence,
            "scope":"Supplied registered tracks only; exact common timestamps and point IDs"}


def compute(output, *, source=None, motion_scope=None, geometry_aligned=False,
            cut_times=(), max_side=512, freeze_threshold=0.001, min_valid_fraction=0.1,
            accounting_scope=None):
    from planner_harness.accounting import run_compute
    from planner_harness.common import sha
    inputs = {'output':str(output),'output_sha256':sha(output),'source':str(source) if source else None,
              'source_sha256':sha(source) if source else None,'motion_scope':motion_scope,
              'geometry_aligned':geometry_aligned,'cut_times':list(cut_times),'max_side':max_side,
              'freeze_threshold':freeze_threshold,'min_valid_fraction':min_valid_fraction,'implementation':sha(__file__)}
    return run_compute('compute:temporal',inputs,lambda:_compute(output,source=source,motion_scope=motion_scope,
        geometry_aligned=geometry_aligned,cut_times=cut_times,max_side=max_side,freeze_threshold=freeze_threshold,
        min_valid_fraction=min_valid_fraction),binding=accounting_scope)
