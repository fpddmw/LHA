"""Low-to-high evaluation. Export by default; API calls require --execute."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT / "src"))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest="command",required=True)
    for name in ("plan","score","compare"):
        p=commands.add_parser(name)
        p.add_argument("--source",required=True)
        p.add_argument("--request-file",required=True,type=Path)
        p.add_argument("--output",required=True,type=Path)
        p.add_argument("--execute",action="store_true")
        p.add_argument("--budget-config",type=Path)
        if name=="plan":
            p.add_argument("--body",type=Path,help="Optional track and evidence/motion configuration; original task only")
            p.add_argument("--track",choices=["short","long"],default="long")
        else:
            p.add_argument("--plan",required=True,type=Path)
            p.add_argument("--judge",choices=["glm5.3flash","sonnet-5.5high"],default="glm5.3flash")
        if name=="score": p.add_argument("--candidate",required=True)
        if name=="compare":
            p.add_argument("--left",required=True);p.add_argument("--right",required=True)
            p.add_argument("--seed",type=int,default=0)
    p=commands.add_parser("temporal")
    p.add_argument("--candidate",required=True);p.add_argument("--source")
    p.add_argument("--plan",type=Path);p.add_argument("--request-file",type=Path)
    p.add_argument("--geometry-aligned",action="store_true")
    p.add_argument("--cut-times",nargs="*",type=float,default=[])
    p.add_argument("--output",required=True,type=Path)
    p=commands.add_parser("features")
    p.add_argument("--candidate",required=True);p.add_argument("--clip-revision",required=True)
    p.add_argument("--dino-revision",required=True);p.add_argument("--device",default="cpu")
    p.add_argument("--output",required=True,type=Path)
    p=commands.add_parser("summary")
    p.add_argument("--records",required=True,type=Path);p.add_argument("--output",required=True,type=Path)
    p.add_argument("--kind",choices=["scores","paired","blind"],default="scores")
    # Local diagnostics remain usable without quotes; real model/GPU work requires a live policy.
    for command_parser in (commands.choices["temporal"],commands.choices["features"]):
        command_parser.add_argument("--budget-config",type=Path)
    args=parser.parse_args()
    from planner_harness.accounting import install,scope,bind
    if args.command=="plan" and args.execute:parser.error("plan is local; omit --execute")
    real = bool(getattr(args,"execute",False) or args.command=="features")
    budget_directory = args.output if args.command in {"plan","score","compare"} else args.output.parent
    budget_scope = None
    if real and args.command not in {"score","compare"} and not getattr(args,"budget_config",None):parser.error("Real execution requires --budget-config with explicit quotes and allowance")
    if getattr(args,"budget_config",None) and args.command not in {"score","compare"}:
        from planner_harness.common import load as read_budget
        target = "compute:features" if args.command=="features" else "compute:temporal" if args.command=="temporal" else "model:"+("glm5.3flash/none" if args.command=="plan" or args.judge=="glm5.3flash" else "sonnet-5.5high/high")
        budget_root = install(budget_directory/"accounting",read_budget(args.budget_config),require_live=real,required_quotes=(target,"compute:features","compute:temporal") if args.command=="score" else (target,))
        budget_scope = scope(budget_root,"standalone-"+args.command)
        bind(budget_directory,budget_scope)
    if args.command=='score' and args.budget_config:
        from planner_harness.common import load as read_compute_budget
        budget_root=install(budget_directory/'compute-accounting',read_compute_budget(args.budget_config),require_live=True,required_quotes=('compute:features','compute:temporal'))
        budget_scope=scope(budget_root,'standalone-final-compute','independent')
    if real:
        from planner_harness.supervisor import maybe_supervise_cli
        if maybe_supervise_cli(budget_directory,[__file__,*sys.argv[1:]]):return
    from planner_harness.common import load
    from planner_harness.execution import immutable
    from planner_harness.video import Video
    from evaluation.low_high import freeze_plan,generate_plan,prepare_plan_request,check_plan
    if args.command in {"plan","score","compare"}:
        source=Video(args.source,args.output / "source-info").info
        request=args.request_file.read_text(encoding="utf-8")
        from evaluation.creative import make_judge,judge_candidate,prepare_final_request
        if args.command=="plan":
            result=freeze_plan({"track":args.track,**(load(args.body) if args.body else {})},request,source,args.output)
        else:
            plan=check_plan(load(args.plan),request,source)
            judge=make_judge(args.judge) if args.execute else None
            if args.command=="score":
                candidate=Video(args.candidate,args.output / "candidate-info").info
                if args.execute:
                    result=judge_candidate(request,source,candidate,args.output,model=judge,plan=plan)
                    from evaluation.final_suite import automatic
                    result={**result,'automatic':automatic(source,candidate,plan,args.output/'automatic-metrics',accounting_scope=budget_scope)}
                    immutable(args.output/'suite.json',result)
                else:
                    packet,images=prepare_final_request(request,source,candidate,args.output,plan=plan)
                    result={"status":"overview_request_export_only","images":len(images),"model_calls":0,"temporal":"unknown until event reviews execute"}
            else:
                from evaluation.pairwise import compare
                result=compare(request,source,Video(args.left,args.output).info,Video(args.right,args.output).info,
                               args.output,plan=plan,seed=args.seed,model=judge)
        print(json.dumps({"status":result.get("status","saved"),"output":str(args.output)},ensure_ascii=False))
    elif args.command=="temporal":
        scope=None
        if args.plan:
            if not args.source or not args.request_file: parser.error("--plan requires --source and --request-file for identity verification")
            source=Video(args.source,args.output.parent).info
            scope=check_plan(load(args.plan),args.request_file.read_text(encoding="utf-8"),source)["task"]["motion_preservation"]
        from evaluation.temporal import compute
        immutable(args.output,compute(args.candidate,source=args.source,motion_scope=scope,geometry_aligned=args.geometry_aligned,cut_times=args.cut_times,accounting_scope=budget_scope))
    elif args.command=="features":
        import re
        if not all(re.fullmatch(r"[0-9a-fA-F]{40}",r) for r in (args.clip_revision,args.dino_revision)):
            parser.error("Formal feature runs require exact 40-character model commit revisions")
        from evaluation.features import compute
        immutable(args.output,compute(args.candidate,clip_revision=args.clip_revision,dino_revision=args.dino_revision,device=args.device,sample_fps=4.0,accounting_scope=budget_scope))
    else:
        from evaluation.low_high_summary import summarize,paired
        from evaluation.pairwise import summary
        immutable(args.output,{"scores":summarize,"paired":paired,"blind":summary}[args.kind](load(args.records)))


if __name__=="__main__":
    from planner_harness.supervisor import cli_entry
    cli_entry(main)
