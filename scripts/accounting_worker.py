"""Resident process owns original model/GPU work after a coordinator deadline."""
import argparse
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("root","output","host"):parser.add_argument("--"+field,required=True,type=Path)
    parser.add_argument("--device",required=True)
    args = parser.parse_args()
    from planner_harness.common import load,save
    from planner_harness.accounting import active
    from experiments.creative_benchmark import init_worker,run_arm,worker_state
    directory = args.output/"supervised-workers"/args.device
    host = load(args.host)
    init_worker(args.device,str(args.root),str(args.output),host)
    while True:
        if active():
            save(directory/"status.json",{"state":"quarantined","resource_released":False,
                 "operations":[{k:v for k,v in item.items() if k!="thread"} for item in active()]})
            time.sleep(.2)
            continue
        if (directory/"stop-request.json").exists():
            # Construct no renderer on a worker that never received a command.
            from experiments import creative_benchmark
            if creative_benchmark._WORKER is not None:
                from server_runtime.service import Service
                Service.close(creative_benchmark._WORKER[3])
            save(directory/"exited.json",{"state":"drained","active_operations":0})
            return
        save(directory/"status.json",{"state":"idle"})
        found = False
        for path in sorted((directory/"commands").glob("*.json")):
            target = directory/"results"/path.name
            if target.exists():continue
            found = True
            if (directory/"started"/path.name).exists():
                save(target,{"error":"Prior worker dispatch has no committed result; no replay","outcome_unknown":True})
                continue
            save(directory/"started"/path.name,{"state":"submitted"})
            command = load(path)
            try:save(target,{"result":run_arm(command["topic"],command["arm"])})
            except BaseException as exc:save(target,{"error":type(exc).__name__,"failure_kind":getattr(exc,"failure_kind",None),"outcome_unknown":getattr(exc,"outcome_unknown",False)})
            break
        if not found:time.sleep(.1)


if __name__ == "__main__":main()
