"""Internal warm per-device worker; public entry is run_creative_benchmark run."""
import argparse,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from planner_harness.common import load
from experiments.device_scheduler import worker
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('root','output','host-config','device'):p.add_argument('--'+name,required=True)
    p.add_argument('--scheduler-pid',type=int);p.add_argument('--scheduler-birth')
    a=p.parse_args()
    import signal
    def stop(signum,frame):
        from planner_harness import accounting
        for item in accounting.active():
            if item.get('owner')==str((Path(a.output)/'workers'/a.device).resolve()):
                accounting.freeze_task(accounting.scope(item['root'],item['topic'],item['lane']),reason='owning scheduler stopped')
        raise KeyboardInterrupt('Owning scheduler stopped this device worker')
    signal.signal(signal.SIGTERM,stop)
    if a.scheduler_pid:
        import ctypes,os
        from planner_harness.owned_process import birth
        # A killed supervisor cannot leave its GPU workers silently running.
        if ctypes.CDLL(None).prctl(1,signal.SIGTERM,0,0,0)!=0:raise RuntimeError('Cannot bind worker parent-death stop')
        if os.getppid()!=a.scheduler_pid or birth(a.scheduler_pid)!=a.scheduler_birth:raise SystemExit('Owning scheduler already exited')
    worker(a.root,a.output,load(a.host_config),a.device)
