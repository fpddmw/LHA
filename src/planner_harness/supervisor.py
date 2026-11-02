"""Detached ownership: supervisors never kill or join an unresolved external call."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

from .common import load,save
from .accounting import ExternalExecutionUnknown,BudgetConfigurationError,active,load_ledger
from .integrity import IntegrityError
from .execution import immutable
from .resources import ResourceExhausted


class ResidentWorker:
    def __init__(self,root,output,device,host_file):
        self.directory = Path(output)/"supervised-workers"/str(device)
        self.directory.mkdir(parents=True,exist_ok=True)
        command = [sys.executable,str(Path(root)/"scripts/accounting_worker.py"),
                   "--root",str(root),"--output",str(output),"--device",str(device),"--host",str(host_file)]
        log = (self.directory/"worker.log").open("ab")
        try:
            self.process = subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
        finally:log.close()
        save(self.directory/"supervisor.json",{"pid":self.process.pid,"command":command,"ownership":"detached; never terminated by the coordinator"})

    def execute(self,topic,arm,*,timeout):
        status = self.directory/"status.json"
        if status.exists() and load(status).get("state") == "quarantined":
            raise ResourceExhausted("Resident worker retains an unresolved operation; no new work dispatched")
        identity = topic["id"]+"__"+arm
        command = self.directory/"commands"/(identity+".json")
        result = self.directory/"results"/(identity+".json")
        immutable(command,{"topic":topic,"arm":arm})
        deadline = time.monotonic()+timeout
        while not result.exists():
            if self.process.poll() is not None:
                raise ExternalExecutionUnknown("Worker exited without a committed result; inspect its original request")
            if time.monotonic()>=deadline:
                save(self.directory/(identity+"-supervisor-timeout.json"),{"pid":self.process.pid,"status":"execution_unknown","action":"retained original worker and its device ownership; no retry"})
                raise ExternalExecutionUnknown("Supervisor deadline reached; resident worker was retained")
            time.sleep(.1)
        saved = load(result)
        if saved.get("error"):
            if saved.get("failure_kind")=="integrity_error":raise IntegrityError("Worker integrity validation failed; inspect original result")
            if saved.get("failure_kind")=="resource_exhausted":raise ResourceExhausted("Worker admission budget exhausted")
            if not saved.get("outcome_unknown",False):raise RuntimeError("Worker failed before a settlement: "+saved["error"])
            raise ExternalExecutionUnknown("Resident operation needs reconciliation: "+saved["error"])
        return saved["result"]

    def close(self,*,wait_seconds=1):
        save(self.directory/"stop-request.json",{"action":"drain when original work has finished"})
        try:self.process.wait(timeout=wait_seconds)
        except subprocess.TimeoutExpired:
            save(self.directory/"retained.json",{"pid":self.process.pid,"state":"owned_or_draining","resource_released":False})


def maybe_supervise_cli(output,argv):
    """Call after parsing/validating a live command, before constructing clients."""
    if os.environ.get("LHA_ACCOUNTING_CHILD") == "1":
        return False
    directory = Path(output)
    directory.mkdir(parents=True,exist_ok=True)
    policy = load(directory / "accounting/policy.json")
    ledger = load_ledger(directory / "accounting")
    remaining = policy["batch"]["wall_seconds"] - (time.time() - (ledger["started_unix"] or time.time()))
    if policy.get("online_task_budget"):remaining = float("inf")
    if remaining <= 0:
        raise ResourceExhausted("Batch wall allowance already expired; no child was started")
    token = uuid.uuid4().hex
    result = directory/("supervised-"+token+".json")
    env = {**os.environ,"LHA_ACCOUNTING_CHILD":"1","LHA_ACCOUNTING_RESULT":str(result)}
    log = directory/("supervised-"+token+".log")
    with log.open("ab") as stream:
        proc = subprocess.Popen([sys.executable,*argv],stdin=subprocess.DEVNULL,stdout=stream,stderr=stream,env=env,start_new_session=True)
    # Child stage deadlines write this result even while the owned call remains
    # alive. No context-manager or executor shutdown waits for that same call.
    deadline = time.monotonic()+remaining+10
    while not result.exists():
        if proc.poll() is not None:
            raise ExternalExecutionUnknown("Execution child exited without a durable status; inspect "+str(log))
        if time.monotonic() >= deadline:
            save(directory/"accounting/stop-submissions.json",{"reason":"supervisor wall deadline","pid":proc.pid,"resource_released":False})
            save(directory/("supervised-"+token+"-timeout.json"),{"pid":proc.pid,"status":"execution_unknown","resource_released":False})
            raise ExternalExecutionUnknown("Supervisor deadline reached; child ownership was retained and new admissions stopped")
        time.sleep(.1)
    saved = load(result)
    if saved["status"] != "complete":
        if saved.get("failure_kind")=="integrity_error":raise IntegrityError("Supervised integrity validation failed; inspect "+str(result))
        if saved.get("failure_kind")=="budget_configuration":raise BudgetConfigurationError("Supervised budget validation failed; inspect "+str(result))
        if saved.get("failure_kind")=="resource_exhausted":raise ResourceExhausted("Supervised allowance exhausted; inspect "+str(result))
        if saved["status"]=="failed":raise RuntimeError("Supervised command failed; inspect "+str(result))
        raise ExternalExecutionUnknown("Supervised command retained outcome "+saved["status"]+"; see "+str(result))
    return True


def cli_entry(main):
    marker = os.environ.get("LHA_ACCOUNTING_RESULT")
    try:
        result = main()
    except BaseException as exc:
        if marker:save(marker,{"status":"execution_unknown" if getattr(exc,"outcome_unknown",False) else "failed","error_type":type(exc).__name__,"failure_kind":getattr(exc,"failure_kind",None),"owned_operations":[{k:v for k,v in item.items() if k!="thread"} for item in active()]})
        raise
    if marker:save(marker,{"status":"complete"})
    return result
