"""Signed render-only handoff over SSH. Planner/Critic credentials stay local."""
from pathlib import Path, PurePosixPath
import json
import os
import shlex
import time

from .common import load, save, sha
from .execution import signature


class UncertainRender(RuntimeError):
    outcome_unknown = True


class FailedRender(RuntimeError):
    pass


def verify_response(job, response, local_video):
    if response.get("request_sha256") != job["sha256"] or response.get("mode") != job["mode"]:
        raise ValueError("Remote receipt belongs to another signed job")
    if response.get("status") != "complete":
        raise RuntimeError("Remote renderer reported a failed job")
    payload = response["payload"]
    if sha(local_video) != payload["video"]["sha256"]:
        raise ValueError("Transferred output hash mismatch")
    receipt = payload["execution"]
    if receipt.get("input_sha256") != job["payload"]["input"]["sha256"] or receipt.get("effective_prompt") != job["payload"]["prompt"] or receipt.get("seed") != job["payload"]["renderer"].get("seed"):
        raise ValueError("Remote renderer input/prompt/seed mismatch")
    payload["video"]["path"] = str(Path(local_video).resolve())
    return payload


class RemoteRenderer:
    def __init__(self, config):
        self.config = config
        root = PurePosixPath(config["root"])
        if not root.is_absolute() or ".." in root.parts or str(root) == "/":
            raise ValueError("Use a dedicated absolute remote workspace")
        self.root = str(root)
        if config.get("poll_seconds", 30) < 1 or config.get("timeout_seconds", 7200) < 1:
            raise ValueError("Remote poll and timeout intervals must be positive")

    def connect(self):
        import paramiko
        ssh = paramiko.SSHClient()
        ssh.load_system_host_keys()
        if self.config.get("known_hosts"):
            ssh.load_host_keys(self.config["known_hosts"])
        # Reject unknown host keys; credentials are read from the environment only.
        ssh.connect(self.config["host"], port=self.config.get("port", 22), username=self.config.get("username", "root"),
                    password=os.environ.get(self.config.get("password_env", "LHA_RENDER_SSH_PASSWORD")),
                    key_filename=self.config.get("key_filename"), timeout=30)
        return ssh

    def __call__(self, job, directory):
        if job["kind"] != "generate" or job["payload"]["renderer"].get("backend") != "ditto" or signature({k:v for k,v in job.items() if k != "sha256"}) != job["sha256"]:
            raise ValueError("Remote handoff accepts signed Ditto render jobs only")
        directory = Path(directory)
        local_input = Path(job["payload"]["input"]["path"])
        if sha(local_input) != job["payload"]["input"]["sha256"]:
            raise ValueError("Conditioning input changed")
        ssh = self.connect()
        try:
            remote = self.root + "/jobs/" + job["sha256"]
            def command(argv):
                _, stdout, stderr = ssh.exec_command(shlex.join(argv))
                result = stdout.read().decode()
                if stdout.channel.recv_exit_status():
                    raise RuntimeError("Remote file operation failed")
                return result
            command(["mkdir", "-p", remote])
            with ssh.open_sftp() as sftp:
                def exists(path):
                    try:
                        sftp.stat(path); return True
                    except FileNotFoundError:
                        return False
                    except OSError as e:
                        if getattr(e, "errno", None) == 2:
                            return False
                        raise
                remote_request, remote_input = remote + "/request.json", remote + "/input" + local_input.suffix
                if not exists(remote_request):
                    with sftp.open(remote_request + ".part", "w") as f:
                        f.write(json.dumps(job, ensure_ascii=False))
                    sftp.rename(remote_request + ".part", remote_request)
                else:
                    with sftp.open(remote_request) as f:
                        if json.loads(f.read()) != job:
                            raise ValueError("Remote request changed")
                if not exists(remote_input):
                    sftp.put(str(local_input), remote_input + ".part")
                    if command(["sha256sum", remote_input + ".part"]).split()[0] != job["payload"]["input"]["sha256"]:
                        raise ValueError("Transferred conditioning hash mismatch")
                    sftp.rename(remote_input + ".part", remote_input)
                if command(["sha256sum", remote_input]).split()[0] != job["payload"]["input"]["sha256"]:
                    raise ValueError("Remote conditioning changed")
                response_path = remote + "/response.json"
                claim = remote + "/dispatch.claim"
                if not exists(response_path) and not exists(claim):
                    if not self.config.get("allow_dispatch", True):
                        raise UncertainRender("No existing remote dispatch to fetch; no job was launched")
                    with sftp.open(claim, "wx") as f:
                        f.write(job["sha256"])
                    argv = [self.config["python"], self.config["repo"].rstrip("/") + "/scripts/run_planner_worker.py",
                            "--request", remote_request, "--input-video", remote_input, "--root", self.config["repo"],
                            "--verified-manifest", self.config["verified_manifest"]]
                    # Only quoted configured paths and signed job paths enter the remote shell.
                    launch = "nohup " + shlex.join(argv) + " > " + shlex.quote(remote + "/worker.log") + " 2>&1 < /dev/null &"
                    _, out, _ = ssh.exec_command(launch)
                    if out.channel.recv_exit_status():
                        raise UncertainRender("Remote dispatch outcome is uncertain; preserve the claim and inspect it")
                save(directory / "remote-handoff.json", {"request_sha256": job["sha256"], "remote_job": remote,
                    "host": self.config["host"], "scope": "Render only; no model API credentials transferred"})
                deadline = time.monotonic() + self.config.get("timeout_seconds", 7200)
                while not exists(response_path):
                    if time.monotonic() >= deadline:
                        raise UncertainRender("Remote job is still unresolved; fetch the same signed job later")
                    time.sleep(self.config.get("poll_seconds", 30))
                with sftp.open(response_path) as f:
                    response = json.loads(f.read())
                save(directory / "remote-response.json", response)
                if response.get("status") != "complete":
                    if response.get("outcome_unknown"):
                        raise UncertainRender("Remote worker needs dispatch reconciliation")
                    raise FailedRender("Remote render failed; preserved remote-response.json contains diagnostics")
                local_video = directory / ("remote-output" + PurePosixPath(response["payload"]["video"]["path"]).suffix)
                remote_video = PurePosixPath(response["payload"]["video"]["path"])
                if not remote_video.is_relative_to(PurePosixPath(remote)):
                    raise ValueError("Remote output escaped its signed job directory")
                sftp.get(str(remote_video), str(local_video) + ".part")
                Path(str(local_video) + ".part").replace(local_video)
                return verify_response(job, response, local_video)
        except (UncertainRender, FailedRender):
            raise
        except Exception as exc:
            raise UncertainRender("Remote execution or transfer is unresolved; inspect or fetch the same signed job") from exc
        finally:
            ssh.close()

    def close(self):
        pass
