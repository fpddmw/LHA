"""Authorize ChatGPT plan usage and probe the exact text/image API used by LHA."""

from __future__ import annotations

import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import sys
import time
import urllib.parse
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from vlm import chatgpt_auth as auth  # noqa: E402


def login(args):
    result = {}
    pending = {}
    authorization_url = ""

    class Callback(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_GET(self):
            parsed = urllib.parse.urlsplit(self.path)
            if parsed.path == "/":
                self.send_response(302)
                self.send_header("Location", authorization_url)
                self.end_headers()
                return
            if parsed.path != "/auth/callback":
                self.send_error(404)
                return
            try:
                result.update(auth.finish_sign_in(args.credential_file, pending, parsed.query))
                status, message = 200, "LHA sign-in completed. You can close this tab."
            except Exception as exc:
                result.update(status="failed", error_type=type(exc).__name__)
                status, message = 400, "LHA sign-in failed. Return to the task for the next step."
            self.send_response(status)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(message.encode())

    with HTTPServer(("127.0.0.1", args.port), Callback) as server:
        server.timeout = 1
        port = server.server_address[1]
        authorization_url, pending = auth.begin_sign_in(
            args.credential_file, f"http://127.0.0.1:{port}/auth/callback"
        )
        url = f"http://127.0.0.1:{port}/"
        ready = {"status": "awaiting_browser_authorization", "login_url": url}
        if args.status_file:
            args.status_file.parent.mkdir(parents=True, exist_ok=True)
            args.status_file.write_text(json.dumps(ready, indent=2))
        print(json.dumps(ready), flush=True)
        if not args.no_browser:
            webbrowser.open(url)
        deadline = time.monotonic() + args.wait_seconds
        while not result and time.monotonic() < deadline:
            server.handle_request()
        result = result or {"status": "authorization_timed_out"}
        if args.status_file:
            args.status_file.write_text(json.dumps(result, indent=2))
        print(json.dumps(result), flush=True)
        return 0 if result.get("status") == "signed_in" else 1


def probe_planner(args, client):
    """Make one diagnostic planning call from a saved input; execute no action."""
    from planner_harness.common import sha
    from planner_harness.creative_actions import ACTIONS
    from planner_harness.json_output import decode_object
    from planner_harness.model_call import metered_text

    raw_input = args.probe_input.read_bytes()
    binding = json.loads(raw_input)
    images = binding.get("images", [])
    for image in images:
        if sha(image["path"]) != image["sha256"]:
            raise ValueError("Probe image differs from the saved Planner input")
    directory = args.output / "planner-call"
    answer = metered_text(
        directory,
        client,
        binding["system_prompt"],
        binding["user_text"],
        [image["path"] for image in images],
    )
    result = json.loads((directory / "attempts/01/result.json").read_text())
    audit = result["client_execution"]
    try:
        parsed = decode_object(answer)
        action = parsed.get("action", parsed.get("tool"))
        valid = action in ACTIONS and isinstance(parsed.get("arguments", {}), dict)
        parse_error = None
    except ValueError as exc:
        parsed, action, valid, parse_error = None, None, False, type(exc).__name__
    passed = valid and audit.get("terminal_event") == "response.completed"
    receipt = {
        "status": "passed" if passed else "failed",
        "kind": "planner_format_probe",
        "source_input_sha256": hashlib.sha256(raw_input).hexdigest(),
        "model": client.model,
        "action": action,
        "parse_error": parse_error,
        "action_executed": False,
        "usage": result.get("usage"),
        "client_execution": audit,
    }
    (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2))
    print(json.dumps(receipt))
    return 0 if passed else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=["login", "status", "models", "probe", "probe-planner", "serve"]
    )
    parser.add_argument("--credential-file")
    parser.add_argument(
        "--probe-input", type=Path, help="Saved Planner transport/input.json for a diagnostic call"
    )
    parser.add_argument(
        "--relay-url", help="Loopback endpoint reached through the owned SSH tunnel"
    )
    parser.add_argument(
        "--audit-dir",
        type=Path,
        help="Relay stream evidence directory; defaults beside its credential file",
    )
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--wait-seconds", type=int, default=1800)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--status-file", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "out/chatgpt_subscription_probe")
    args = parser.parse_args()
    if args.command == "probe-planner" and args.probe_input is None:
        parser.error("probe-planner requires --probe-input")
    if args.command == "login":
        return login(args)
    if args.command == "status":
        print(json.dumps(auth.credential_status(args.credential_file)))
        return 0
    if args.command == "serve":
        from vlm.chatgpt_relay import make_server

        with make_server(args.port, args.credential_file, audit_dir=args.audit_dir) as server:
            print(
                json.dumps(
                    {"status": "serving", "bind": "127.0.0.1", "port": server.server_address[1]}
                ),
                flush=True,
            )
            server.serve_forever()
        return 0
    from vlm.chatgpt_subscription import ChatGPTSubscriptionVisionModel

    client = ChatGPTSubscriptionVisionModel(
        credential_file=args.credential_file, relay_url=args.relay_url
    )
    models = client.list_models()
    if args.command == "models":
        print(json.dumps(models))
        return 0
    if client.api_model not in {row["slug"] for row in models}:
        raise RuntimeError(
            "The authorized account does not list the requested GPT-6.1-sol; no model substituted"
        )
    if args.command == "probe-planner":
        return probe_planner(args, client)
    from PIL import Image, ImageDraw
    from planner_harness.model_call import metered_text

    args.output.mkdir(parents=True, exist_ok=True)
    frame = Image.new("RGB", (200, 100), "red")
    ImageDraw.Draw(frame).rectangle((100, 0, 199, 99), fill="blue")
    path = args.output / "red-blue.png"
    frame.save(path)
    answer = metered_text(
        args.output / "image-call",
        client,
        'Return JSON {"left":"color","right":"color"}.',
        "Name the left and right colors in this image.",
        [str(path)],
    )
    from planner_harness.json_output import decode_object

    parsed = decode_object(answer)
    passed = (
        str(parsed.get("left", "")).lower() == "red"
        and str(parsed.get("right", "")).lower() == "blue"
    )
    receipt = {
        "status": "passed" if passed else "failed",
        "model": client.model,
        "answer": parsed,
        "transport": client.runtime_identity(),
        "available_models": [r["slug"] for r in models],
    }
    (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2))
    print(json.dumps(receipt))
    return 0 if passed else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        # Auth/token errors may embed request context; expose only a safe diagnostic.
        print(
            json.dumps(
                {
                    "status": "failed",
                    "error_type": type(exc).__name__,
                    "diagnostic": getattr(exc, "safe_diagnostic", None),
                }
            ),
            file=sys.stderr,
        )
        raise SystemExit(1) from None
