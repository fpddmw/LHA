"""Prepare a local protocol migration plan; does not apply it or call a model/renderer."""
import argparse
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--run',type=Path)
    mode.add_argument('--baseline-batch',type=Path)
    parser.add_argument('--baseline-profile',type=Path)
    parser.add_argument('--reason')
    parser.add_argument('--profile',type=Path,help='Distinct new shared experiment profile, if the run has one')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    from planner_harness.protocol_migration import plan,prepare_batch
    from planner_harness.execution import immutable
    if args.baseline_batch:
        if not args.baseline_profile:parser.error('Batch preparation requires --baseline-profile')
        result=prepare_batch(ROOT,args.baseline_batch,args.baseline_profile,args.output)
    else:
        if not args.reason:parser.error('Run preparation requires --reason')
        result=plan(args.run,ROOT,args.reason,profile=args.profile)
        immutable(args.output,result)
    print('Migration plan saved. No state migration, model/render call, dispatch resume or heartbeat change performed.')


if __name__=='__main__':main()
