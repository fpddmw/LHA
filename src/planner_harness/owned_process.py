"""Cancellation evidence for children launched by this runtime, never arbitrary PIDs."""
import os
from pathlib import Path
import signal
import subprocess
import threading


def birth(pid):
    try:
        return Path(f"/proc/{pid}/stat").read_text().rsplit(")",1)[1].split()[19]
    except (OSError, IndexError):
        return None


class OwnedProcess:
    def __init__(self, command, **kwargs):
        self.lock = threading.Lock()
        self.process = subprocess.Popen(command, start_new_session=True, **kwargs)
        self.pid = self.process.pid
        self.birth = birth(self.pid)

    def cancel(self):
        with self.lock:
            if self.process.poll() is not None:
                return {"pid":self.pid,"local_stopped":True,"returncode":self.process.returncode,"external_stopped":False}
            if self.birth is None or birth(self.pid) != self.birth:
                return {"pid":self.pid,"local_stopped":False,"reason":"Process identity could not be verified","external_stopped":False}
            # start_new_session makes this a group owned exclusively by this call.
            os.killpg(self.pid, signal.SIGTERM)
            try:self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                os.killpg(self.pid, signal.SIGKILL)
                try:self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:pass
            return {"pid":self.pid,"birth":self.birth,"local_stopped":self.process.poll() is not None,
                    "returncode":self.process.poll(),"external_stopped":False,
                    "scope":"Local owned process group; provider execution remains unknown without a provider receipt"}
