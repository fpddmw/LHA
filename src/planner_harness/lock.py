"""Process-scoped run lock, released by the OS after interruption."""
import os
import hashlib
import tempfile
from pathlib import Path


class RunLock:
    def __init__(self, output):
        output = Path(output).resolve()
        # Windows byte-range locking is unsupported on some WSL UNC shares.
        # Keep its OS-released lock on the local host; Linux uses flock in the run.
        if os.name == "nt":
            key = str(output).lower().replace("\\\\wsl$\\", "\\\\wsl.localhost\\")
            self.path = Path(tempfile.gettempdir()) / "lha-planner-locks" / (hashlib.sha256(key.encode()).hexdigest() + ".lock")
        else:
            self.path = output / ".run.lock"

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.file = self.path.open("a+b")
        self.file.seek(0, 2)
        if self.file.tell() == 0:
            self.file.write(b"0")
            self.file.flush()
        self.file.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.file.close()
            raise RuntimeError("This run is already owned by another process") from None
        return self

    def __exit__(self, *_):
        self.file.close()
