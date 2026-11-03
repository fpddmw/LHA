"""Process-local guard inherited by Python children of the public smoke command."""
import importlib.abc
from pathlib import Path
import sys


class NoModelLibraries(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'torch', 'transformers', 'cupy', 'diffsynth', 'bernini'}:
            raise ImportError('Model/GPU libraries are disabled in offline smoke: ' + fullname)
        return None


def install():
    sys.meta_path.insert(0, NoModelLibraries())

    def audit(event, args):
        if event in {'socket.connect', 'socket.getaddrinfo', 'socket.sendto'}:
            raise RuntimeError('Network is disabled in the public offline smoke test')
        if event == 'subprocess.Popen':
            executable = Path(str(args[0])).name.lower()
            permitted = {Path(sys.executable).name.lower(), 'ffmpeg', 'ffmpeg.exe', 'ffprobe', 'ffprobe.exe'}
            if executable not in permitted:
                raise RuntimeError('Unapproved subprocess in offline smoke: ' + executable)
        if event == 'os.system':
            raise RuntimeError('Shell execution is disabled in offline smoke')
    sys.addaudithook(audit)
