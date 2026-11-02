"""Drain separately budgeted post-batch training-task (explicit opt-in) experience contributions."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--config',type=Path)
    args=p.parse_args()
    from planner_harness.common import load
    from planner_harness.maintenance import drain
    print(json.dumps(drain(ROOT,args.output,load(args.config) if args.config else None)))

if __name__=='__main__':main()
