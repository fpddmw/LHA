"""Fallback: fetch pinned public weights locally, verify, and transfer over SSH.

Requires huggingface-hub, hf-xet and paramiko on the local computer. Credentials
are read interactively or from stdin and are never written to the project.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import getpass
import hashlib
import json
from pathlib import Path, PurePosixPath
import shlex
import sys

from huggingface_hub import HfApi, hf_hub_download
import paramiko

REPO = "ByteDance/Bernini-R-1.3B-Diffusers"
REVISION = "ff4c5d4d2d31365c2ffeb30e9753065ee18f58ce"


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, default=22)
    parser.add_argument("--user", default="root")
    parser.add_argument("--remote-root", default="/openbayes/home/LHA/models/Bernini-R-1.3B-Diffusers")
    parser.add_argument("--known-hosts", type=Path, default=Path.home() / ".ssh/known_hosts")
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--password-stdin", action="store_true")
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    password = sys.stdin.readline().rstrip("\r\n") if args.password_stdin else getpass.getpass("SSH password: ")
    info = HfApi().model_info(REPO, revision=REVISION, files_metadata=True)
    entries = [f for f in info.siblings if f.rfilename.endswith((".json", ".safetensors")) or f.rfilename.startswith("tokenizer/") or f.rfilename == "README.md"]
    # Transfer small configuration files first so the remote layout is explicit.
    entries.sort(key=lambda f: f.size or 0)

    def connect():
        client = paramiko.SSHClient()
        client.load_host_keys(str(args.known_hosts))
        client.connect(args.host, port=args.port, username=args.user, password=password,
                       timeout=30, look_for_keys=False, allow_agent=False)
        return client

    def transfer(entry):
        relative = PurePosixPath(entry.rfilename)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("Unsafe model filename")
        remote = args.remote_root.rstrip("/") + "/" + str(relative)
        expected = entry.lfs.sha256 if entry.lfs else None
        client = connect()
        try:
            # Existing complete weight shards from the server download are reused.
            if expected:
                _, stdout, _ = client.exec_command("sha256sum " + shlex.quote(remote))
                existing = stdout.read().decode().split()
                if stdout.channel.recv_exit_status() == 0 and existing and existing[0] == expected:
                    print("REUSED " + str(relative), flush=True)
                    return {"path": str(relative), "bytes": entry.size, "sha256": expected}
            local = hf_hub_download(REPO, str(relative), revision=REVISION, local_dir=args.cache)
            digest = sha256(local)
            if expected and digest != expected:
                raise RuntimeError(f"Source hash mismatch: {relative}")
            # Reconnect after a potentially long download.
            client.close()
            client = connect()
            _, stdout, stderr = client.exec_command("mkdir -p " + shlex.quote(str(PurePosixPath(remote).parent)))
            if stdout.channel.recv_exit_status() != 0:
                raise RuntimeError(stderr.read().decode())
            sftp = client.open_sftp()
            temporary = remote + ".lha-upload"
            sftp.put(local, temporary)
            sftp.close()
            _, stdout, _ = client.exec_command("sha256sum " + shlex.quote(temporary))
            actual = stdout.read().decode().split()
            if stdout.channel.recv_exit_status() != 0 or not actual or actual[0] != digest:
                raise RuntimeError(f"Transfer hash mismatch: {relative}")
            sftp = client.open_sftp()
            sftp.posix_rename(temporary, remote)
            sftp.close()
            print("VERIFIED " + str(relative) + " " + digest, flush=True)
            return {"path": str(relative), "bytes": Path(local).stat().st_size, "sha256": digest}
        finally:
            client.close()

    records, errors = [], []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        jobs = {pool.submit(transfer, entry): entry.rfilename for entry in entries}
        for job in as_completed(jobs):
            try:
                records.append(job.result())
            except Exception as exc:
                errors.append({"path": jobs[job], "error": str(exc)})
                print("FAILED " + jobs[job] + ": " + str(exc), file=sys.stderr, flush=True)
            args.manifest.parent.mkdir(parents=True, exist_ok=True)
            args.manifest.write_text(json.dumps({"repo_id": REPO, "revision": REVISION,
                "files": sorted(records, key=lambda r: r["path"]), "errors": errors}, indent=2), encoding="utf-8")
    if errors:
        raise SystemExit(1)
    client = connect()
    try:
        sftp = client.open_sftp()
        sftp.put(str(args.manifest), args.remote_root.rstrip("/") + "/download-manifest.json")
        sftp.close()
    finally:
        client.close()


if __name__ == "__main__":
    main()
