"""Offline contracts for subscription OAuth and the streamed image transport."""

import io
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import urllib.parse

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from vlm import chatgpt_auth as auth  # noqa: E402
from vlm.chatgpt_subscription import ChatGPTSubscriptionVisionModel, SubscriptionAPIError  # noqa: E402
from planner_harness.accounting import ExternalExecutionUnknown  # noqa: E402


class RelayTLSBoundaryTests(unittest.TestCase):
    def test_handshake_retry_uses_fresh_http_state_and_sends_once(self):
        from http.client import HTTPSConnection
        import ssl
        import urllib.request
        from unittest.mock import Mock
        from vlm.chatgpt_relay import open_upstream

        sock = Mock()
        sock.makefile.return_value = io.BytesIO(
            b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nOK"
        )
        connections = []

        def connect(connection):
            connections.append(connection)
            if len(connections) == 1:
                raise ssl.SSLEOFError("handshake")
            connection.sock = sock

        request = urllib.request.Request("https://fixture.invalid/responses", data=b"{}")
        with patch.object(HTTPSConnection, "connect", autospec=True, side_effect=connect):
            with open_upstream(request, 5) as response:
                self.assertEqual(response.read(), b"OK")
        self.assertEqual(len(connections), 2)
        self.assertIsNot(connections[0], connections[1])
        wire = b"".join(call.args[0] for call in sock.sendall.call_args_list)
        self.assertEqual(wire.count(b"POST "), 1)
        self.assertTrue(wire.endswith(b"\r\n\r\n{}"))
        self.assertEqual(len(request.lha_connect_failures), 1)

    def test_request_write_eof_does_not_repeat_a_started_request(self):
        from http.client import HTTPSConnection
        import ssl
        import urllib.error
        import urllib.request
        from unittest.mock import Mock
        from vlm.chatgpt_relay import open_upstream

        sock = Mock()
        sock.sendall.side_effect = ssl.SSLEOFError("request write interrupted")
        request = urllib.request.Request("https://fixture.invalid/responses", data=b"{}")
        with patch.object(HTTPSConnection, "connect", autospec=True,
                          side_effect=lambda conn: setattr(conn, "sock", sock)) as connect:
            with self.assertRaises(urllib.error.URLError) as raised:
                open_upstream(request, 5)
        self.assertIsInstance(raised.exception.reason, ssl.SSLEOFError)
        self.assertEqual(connect.call_count, 1)
        self.assertEqual(sock.sendall.call_count, 1)
        self.assertEqual(request.lha_connect_failures, [])

    def test_exhausted_handshake_is_proven_predispatch(self):
        from http.client import HTTPSConnection
        import ssl
        import urllib.error
        import urllib.request
        from vlm.chatgpt_relay import open_upstream, UpstreamHandshakeFailed

        request = urllib.request.Request("https://fixture.invalid/responses", data=b"{}")
        with patch.object(HTTPSConnection, "connect", side_effect=ssl.SSLEOFError("handshake")) as connect:
            with self.assertRaises(urllib.error.URLError) as raised:
                open_upstream(request, 5)
        self.assertIsInstance(raised.exception.reason, UpstreamHandshakeFailed)
        self.assertEqual(connect.call_count, 2)
        self.assertEqual(len(request.lha_connect_failures), 2)


def stream(*items):
    return io.BytesIO(b"".join(b"data: " + json.dumps(x).encode() + b"\n\n" for x in items))


def complete(text='{"ok":true}'):
    return {
        "type": "response.completed",
        "response": {
            "id": "resp-fixture",
            "status": "completed",
            "model": "gpt-6.1-sol",
            "usage": {"input_tokens": 12, "output_tokens": 4, "total_tokens": 16},
            "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}],
        },
    }


class SubscriptionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "credentials.json"
        self.token_patch = patch(
            "vlm.chatgpt_subscription.access_token", return_value="private-test-token"
        )
        self.token_patch.start()
        self.addCleanup(self.token_patch.stop)

    def overload_stream(self):
        response = stream(
            {"type": "response.created", "response": {"id": "resp-overloaded"}},
            {"type": "response.in_progress", "response": {"usage": {"total_tokens": 12}}},
            {"type": "response.metadata", "response_id": "resp-overloaded"},
            {"type": "error", "error": {"type": "service_unavailable_error",
                "code": "server_is_overloaded",
                "headers": {"retry-after": "310", "retry-after-ms": "310000"}}},
        )
        response.status = 200
        return response

    def test_sse_overload_preserves_original_stream_and_known_usage(self):
        model = ChatGPTSubscriptionVisionModel()
        model.lha_audit_directory = self.root / "audit"
        response = self.overload_stream()
        raw = response.getvalue()
        with patch.object(model, "_open", return_value=response):
            with self.assertRaises(SubscriptionAPIError) as raised:
                model.predict_text(system_prompt="s", user_text="u", image_paths=[])
        error = raised.exception
        self.assertTrue(error.retryable)
        self.assertEqual(error.safe_diagnostic, {"status": 503, "code": "server_is_overloaded", "retry_after_seconds": 310})
        self.assertEqual(model.last_client_audit["http_status"], 200)
        self.assertEqual(model.last_client_audit["terminal_event"], "error")
        self.assertEqual(model.last_usage, {"total_tokens": 12})
        self.assertEqual((self.root / "audit/stream.bin").read_bytes(), raw)

    def test_sse_overload_cannot_retry_beyond_original_deadline(self):
        from planner_harness import accounting
        from planner_harness.model_call import call_text
        from planner_harness.resources import TaskDeadline

        root = accounting.install(self.root / "accounting", accounting.default_online_policy(wall_seconds=60))
        scope = accounting.scope(root, "fixture", "full")
        accounting.start_task(scope)
        model = accounting.attach(ChatGPTSubscriptionVisionModel(), scope)
        call = self.root / "call"
        with patch.object(model, "_open", return_value=self.overload_stream()) as post:
            with self.assertRaisesRegex(TaskDeadline, "retry-after exceeds"):
                call_text(call, model, "s", "u", [], attempts=2)
        self.assertEqual(post.call_count, 1)
        record = accounting.operation(scope, str(call / "attempts/01"))
        self.assertEqual(record["actual_usage"], {"total_tokens": 12})
        self.assertFalse((call / "attempts/02/submitted.json").exists())

    def test_exact_large_prompt_original_image_and_completed_usage(self):
        image = self.root / "frame.png"
        image.write_bytes(b"fixture-image")
        model = ChatGPTSubscriptionVisionModel()
        with patch(
            "vlm.chatgpt_subscription.urllib.request.urlopen", return_value=stream(complete())
        ) as post:
            value = model.predict_json(
                system_prompt="Only LHA instructions",
                user_text="a" * 167902,
                image_paths=[str(image)],
            )
        self.assertEqual(value, {"ok": True})
        request = post.call_args.args[0]
        body = json.loads(request.data)
        self.assertEqual(len(body["input"][0]["content"][0]["text"]), 167902)
        from vlm.response_contract import INSTRUCTION
        self.assertEqual(body["instructions"], "Only LHA instructions\n\n" + INSTRUCTION)
        self.assertEqual(body["model"], "gpt-6.1-sol")
        self.assertEqual(
            body["input"][0]["content"][1]["image_url"],
            "data:image/png;base64,Zml4dHVyZS1pbWFnZQ==",
        )
        self.assertFalse(body["store"])
        self.assertTrue(body["stream"])
        self.assertNotIn("max_output_tokens", body)
        self.assertNotIn("previous_response_id", body)
        self.assertEqual(model.last_usage["total_tokens"], 16)
        self.assertNotIn("private-test-token", json.dumps(model.last_client_audit))

    def test_partial_stream_is_unknown_not_a_successful_answer(self):
        with patch(
            "vlm.chatgpt_subscription.urllib.request.urlopen",
            return_value=stream({"type": "response.output_text.delta", "delta": '{"ok":true}'}),
        ):
            with self.assertRaises(ExternalExecutionUnknown):
                ChatGPTSubscriptionVisionModel().predict_text(
                    system_prompt="s", user_text="u", image_paths=[]
                )

    def test_terminal_failure_and_incomplete_are_distinct_from_completed(self):
        for kind, field in [
            ("response.failed", {"error": {"code": "subscription_sharing_usage_limit_exceeded"}}),
            ("response.incomplete", {"incomplete_details": {"reason": "max_output_tokens"}}),
        ]:
            with (
                self.subTest(kind=kind),
                patch(
                    "vlm.chatgpt_subscription.urllib.request.urlopen",
                    return_value=stream(
                        {
                            "type": kind,
                            "response": {"id": "fixture", "usage": {"total_tokens": 9}, **field},
                        }
                    ),
                ),
            ):
                model = ChatGPTSubscriptionVisionModel()
                with self.assertRaises(SubscriptionAPIError) as error:
                    model.predict_text(system_prompt="s", user_text="u", image_paths=[])
                self.assertFalse(error.exception.retryable)
                self.assertEqual(model.last_usage["total_tokens"], 9)
                self.assertEqual(model.last_client_audit["terminal_event"], kind)

    def test_sse_multiline_and_comment(self):
        from vlm.chatgpt_subscription import events

        data = io.BytesIO(
            b': heartbeat\nevent: message\ndata: {"type":\ndata: "fixture"}\n\ndata: [DONE]\n\n'
        )
        self.assertEqual(list(events(data)), [{"type": "fixture"}])

    def test_commentary_and_repeated_json_are_not_concatenated_into_final(self):
        event = complete()

        def message(identifier, phase, text):
            return {
                "id": identifier,
                "type": "message",
                "role": "assistant",
                "phase": phase,
                "content": [{"type": "output_text", "text": text}],
            }

        event["response"]["output"] = [
            message("msg-update", "commentary", "I will inspect this. " + '{"action":"observe"}'),
            message("msg-final", "final_answer", '{"action":"generate"}'),
        ]
        client = ChatGPTSubscriptionVisionModel()
        client.lha_audit_directory = str(self.root / "audit")
        with patch.object(client, "_open", return_value=stream(event)):
            self.assertEqual(
                client.predict_json(system_prompt="s", user_text="u", image_paths=[]),
                {"action": "generate"},
            )
        self.assertEqual(client.last_client_audit["selected_message_id"], "msg-final")
        self.assertEqual(client.last_provider_response, event["response"])
        self.assertEqual(
            json.loads((self.root / "audit/response.json").read_text()), event["response"]
        )
        raw = (self.root / "audit/stream.bin").read_bytes()
        self.assertIn(b"I will inspect this.", raw)
        self.assertNotIn(b"private-test-token", raw)

    def test_optional_phase_uses_last_message_and_commentary_only_is_empty(self):
        from vlm.responses_stream import final_answer

        def msg(text, **extra):
            return {"type": "message", "content": [{"type": "output_text", "text": text}], **extra}

        cases = [
            ([msg("first"), msg("last")], "last", "last_unphased"),
            ([msg("progress", phase="commentary")], "", "no_answer"),
            (
                [msg("final", phase="final_answer"), msg("progress", phase="commentary")],
                "final",
                "final_answer",
            ),
            ([msg("user", role="user")], "", "no_answer"),
        ]
        for output, expected, selection in cases:
            with self.subTest(output=output):
                text, evidence = final_answer({"output": output})
                self.assertEqual(text, expected)
                self.assertEqual(evidence["selection"], selection)

    def test_durable_unknown_preserves_raw_stream_and_stage_without_replay(self):
        from planner_harness.model_call import metered_text

        event = {"type": "response.created", "response": {"id": "resp-interrupted"}}
        client = ChatGPTSubscriptionVisionModel()
        directory = self.root / "unknown-call"
        with patch.object(client, "_open", return_value=stream(event)) as post:
            for _ in range(2):
                with self.assertRaises(ExternalExecutionUnknown):
                    metered_text(directory, client, "s", "u", [])
        self.assertEqual(post.call_count, 1)
        attempt = directory / "attempts/01"
        unknown = json.loads((attempt / "unknown.json").read_text())
        self.assertEqual(unknown["client_execution"]["stage"], "eof_without_terminal")
        self.assertEqual(unknown["client_execution"]["response_id"], "resp-interrupted")
        summary = json.loads((attempt / "client-audit/summary.json").read_text())
        self.assertEqual(summary["outcome"], "execution_unknown")
        self.assertEqual(summary["event_count"], 1)
        self.assertIn(b"resp-interrupted", (attempt / "client-audit/stream.bin").read_bytes())

    def test_non_sse_body_and_malformed_sse_remain_diagnosable(self):
        for content_type, raw, stage in [
            ("application/json", b'{"unexpected": "body"}', "eof_without_terminal"),
            ("text/event-stream", b"data: {invalid}\n\n", "read_stream"),
        ]:
            with self.subTest(content_type=content_type):
                response = io.BytesIO(raw)
                response.status = 200
                response.headers = {
                    "Content-Type": content_type,
                    "X-Request-ID": "upstream-fixture",
                    "Authorization": "private-test-token",
                }
                client = ChatGPTSubscriptionVisionModel()
                client.lha_audit_directory = str(self.root / "non-sse")
                with patch.object(client, "_open", return_value=response):
                    with self.assertRaises(ExternalExecutionUnknown):
                        client.predict_text(system_prompt="s", user_text="u", image_paths=[])
                self.assertEqual(client.last_client_audit["stage"], stage)
                self.assertEqual((self.root / "non-sse/stream.bin").read_bytes(), raw)
                self.assertNotIn("private-test-token", json.dumps(client.last_client_audit))

    def test_mislabeled_sse_requires_complete_framed_response(self):
        completed = complete()
        invalid = complete()
        invalid["response"]["status"] = "in_progress"
        cases = [
            (stream(completed).getvalue(), True),
            (
                stream({"type": "response.output_text.delta", "delta": '{"ok":true}'}).getvalue(),
                False,
            ),
            (json.dumps(completed["response"]).encode(), False),
            (stream(invalid).getvalue(), False),
        ]
        for body, success in cases:
            with self.subTest(body=body):
                response = io.BytesIO(body)
                response.status = 200
                response.headers = {"Content-Type": "application/json"}
                client = ChatGPTSubscriptionVisionModel()
                with patch.object(client, "_open", return_value=response):
                    if success:
                        self.assertEqual(
                            client.predict_json(system_prompt="s", user_text="u", image_paths=[]),
                            {"ok": True},
                        )
                    else:
                        with self.assertRaises(ExternalExecutionUnknown):
                            client.predict_text(system_prompt="s", user_text="u", image_paths=[])
                self.assertTrue(client.last_client_audit["content_type_mismatch"])
                self.assertEqual(
                    client.last_client_audit["headers"]["Content-Type"], "application/json"
                )

    def test_split_utf8_crlf_and_final_event_without_trailing_blank(self):
        from vlm.responses_stream import EventDecoder

        raw = ("data: " + json.dumps(complete("中文"), ensure_ascii=False) + "\r\n").encode()
        decoder = EventDecoder()
        values = []
        for byte in raw:
            values.extend(decoder.feed(bytes([byte])))
        values.extend(decoder.finish())
        self.assertEqual(values, [complete("中文")])

    def test_relay_diagnostics_distinguish_connect_read_and_clean_eof(self):
        from http.client import IncompleteRead
        from vlm.chatgpt_relay import make_server

        class Interrupted(io.BytesIO):
            status = 200
            headers = {"Content-Type": "text/event-stream", "X-Request-ID": "upstream-fixture"}

            def read1(self, _):
                raise IncompleteRead(b'data: {"type":"response.created"}\n\n', 100)

        for name, effect, expected_stage in [
            ("connect", ConnectionResetError("connection reset"), "upstream_connect"),
            ("read", Interrupted(), "upstream_read"),
            ("eof", stream({"type": "response.created"}), "upstream_eof"),
        ]:
            with self.subTest(name=name):
                if name == "eof":
                    effect.status, effect.headers = 200, {"Content-Type": "text/event-stream"}
                audit_root = self.root / name
                with make_server(0, str(self.path), audit_dir=audit_root) as server:
                    worker = threading.Thread(target=server.serve_forever, daemon=True)
                    worker.start()
                    try:
                        client = ChatGPTSubscriptionVisionModel(
                            relay_url=f"http://127.0.0.1:{server.server_address[1]}"
                        )
                        client.lha_audit_directory = str(self.root / (name + "-client"))
                        kwargs = (
                            {"side_effect": effect}
                            if isinstance(effect, Exception)
                            else {"return_value": effect}
                        )
                        with (
                            patch(
                                "vlm.chatgpt_relay.access_token", return_value="relay-owner-secret"
                            ),
                            patch("vlm.chatgpt_relay.open_upstream", **kwargs) as post,
                        ):
                            with self.assertRaises(ExternalExecutionUnknown):
                                client.predict_text(
                                    system_prompt="s", user_text="u", image_paths=[]
                                )
                        self.assertEqual(post.call_count, 1)
                    finally:
                        server.shutdown()
                        worker.join()
                summaries = list(audit_root.glob("*/*/summary.json"))
                self.assertEqual(len(summaries), 1)
                summary = json.loads(summaries[0].read_text())
                self.assertEqual(summary["stage"], expected_stage)
                self.assertEqual(summary["request_id"], client.last_client_audit["request_id"])
                self.assertEqual(
                    summary["relay_id"], client.last_client_audit["headers"]["X-LHA-Relay-ID"]
                )
                if name == "read":
                    self.assertEqual(summary["error"]["type"], "IncompleteRead")
                    self.assertGreater(summary["received_bytes"], 0)
                for path in audit_root.rglob("*"):
                    if path.is_file():
                        self.assertNotIn(b"relay-owner-secret", path.read_bytes())

    def test_diagnostic_write_failure_does_not_discard_completed_answer(self):
        client = ChatGPTSubscriptionVisionModel()
        unavailable = self.root / "file-not-directory"
        unavailable.write_text("occupied")
        client.lha_audit_directory = str(unavailable)
        with patch.object(client, "_open", return_value=stream(complete())):
            self.assertEqual(
                client.predict_json(system_prompt="s", user_text="u", image_paths=[]), {"ok": True}
            )
        self.assertIn("audit_write_error", client.last_client_audit)

    def test_relay_downstream_write_error_keeps_received_terminal_evidence(self):
        import socketserver
        from vlm.chatgpt_relay import make_server

        response = stream(complete())
        response.status, response.headers = 200, {"Content-Type": "text/event-stream"}
        original_write = socketserver._SocketWriter.write

        def disconnect(writer, data):
            if data.startswith(b"data:"):
                raise BrokenPipeError("fixture worker disconnected")
            return original_write(writer, data)

        audit_root = self.root / "relay-disconnect"
        with make_server(0, str(self.path), audit_dir=audit_root) as server:
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                with (
                    patch("vlm.chatgpt_relay.access_token", return_value="fixture"),
                    patch("vlm.chatgpt_relay.open_upstream", return_value=response) as post,
                    patch.object(socketserver._SocketWriter, "write", disconnect),
                ):
                    client = ChatGPTSubscriptionVisionModel(
                        relay_url=f"http://127.0.0.1:{server.server_address[1]}"
                    )
                    with self.assertRaises(ExternalExecutionUnknown):
                        client.predict_text(system_prompt="s", user_text="u", image_paths=[])
                post.assert_called_once()
            finally:
                server.shutdown()
                worker.join()
        summary = json.loads(next(audit_root.glob("*/*/summary.json")).read_text())
        self.assertEqual(summary["failure_stage"], "downstream_write")
        self.assertEqual(summary["terminal_event"], "response.completed")
        self.assertTrue(list(audit_root.glob("*/*/response.json")))

    def test_dynamic_registration_state_host_and_pkce(self):
        url, pending = auth.begin_sign_in(self.path, "http://127.0.0.1:18765/auth/callback")
        values = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
        self.assertEqual(values["client_id"], ["dynamic_agent_client"])
        self.assertEqual(values["agent_name_hint"], ["LHA"])
        self.assertNotIn(pending["verifier"], url)
        _, second = auth.begin_sign_in(self.path, pending["redirect_uri"])
        self.assertEqual(pending["ext_agent_host_id"], second["ext_agent_host_id"])
        self.assertNotEqual(pending["state"], second["state"])
        with patch.object(auth, "token_request") as exchange:
            with self.assertRaises(auth.AuthenticationError):
                auth.finish_sign_in(
                    self.path, pending, "state=wrong&code=fixture&client_id=oaiapp_test"
                )
            exchange.assert_not_called()

    def test_callback_uses_issued_client_id_and_token_grants(self):
        _, pending = auth.begin_sign_in(self.path, "http://127.0.0.1:18765/auth/callback")
        tokens = {
            "access_token": "private-access",
            "refresh_token": "private-refresh",
            "id_token": "private-id",
            "scope": auth.SCOPE,
            "expires_in": 3600,
        }
        query = urllib.parse.urlencode(
            {"state": pending["state"], "code": "fixture-code", "client_id": "oaiapp_test"}
        )
        with (
            patch.object(auth, "token_request", return_value=tokens) as exchange,
            patch.object(auth, "validate_identity", return_value={"sub": "fixture-subject"}),
        ):
            self.assertEqual(auth.finish_sign_in(self.path, pending, query)["status"], "signed_in")
        self.assertEqual(exchange.call_args.args[0]["client_id"], "oaiapp_test")
        self.assertEqual(exchange.call_args.args[0]["redirect_uri"], pending["redirect_uri"])
        self.assertTrue(auth.credential_status(self.path)["plan_usage_granted"])
        if os.name != "nt":
            self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_refresh_replaces_rotating_credentials_once(self):
        auth.save_private(
            self.path,
            {
                "client_id": "oaiapp_test",
                "subject": "test",
                "access_token": "old",
                "refresh_token": "old-refresh",
                "scopes": auth.SCOPE.split(),
                "expires_at": 0,
            },
        )
        with patch.object(
            auth,
            "token_request",
            return_value={
                "access_token": "new",
                "refresh_token": "new-refresh",
                "expires_in": 3600,
            },
        ) as exchange:
            self.assertEqual(auth.access_token(self.path), "new")
            self.assertEqual(auth.access_token(self.path), "new")
        exchange.assert_called_once()
        saved = json.loads(self.path.read_text())
        self.assertEqual(saved["refresh_token"], "new-refresh")
        self.assertNotIn("scope", exchange.call_args.args[0])

    def test_signed_id_token_verifies_nonce_issuer_audience(self):
        import jwt
        from cryptography.hazmat.primitives.asymmetric import rsa
        from types import SimpleNamespace

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        token = jwt.encode(
            {
                "sub": "fixture",
                "iat": time.time(),
                "exp": time.time() + 300,
                "iss": auth.ISSUER,
                "aud": "oaiapp_test",
                "nonce": "nonce",
            },
            key,
            algorithm="RS256",
        )
        with patch(
            "jwt.PyJWKClient.get_signing_key_from_jwt",
            return_value=SimpleNamespace(key=key.public_key()),
        ):
            self.assertEqual(
                auth.validate_identity(token, "oaiapp_test", "nonce")["sub"], "fixture"
            )
            with self.assertRaises(auth.AuthenticationError):
                auth.validate_identity(token, "oaiapp_test", "wrong")
            with self.assertRaises(jwt.InvalidAudienceError):
                auth.validate_identity(token, "wrong", "nonce")

    def test_role_factory_and_preflight_support_subscription_without_openrouter_key(self):
        from experiments.preflight import api_model_preflight
        from experiments.unified_benchmark import model_configuration

        config = json.loads((ROOT / "configs/chatgpt-subscription-models.json").read_text())
        for spec in config.values():
            spec["options"]["credential_file"] = str(self.path)
        auth.save_private(self.path, {"access_token": "fixture", "scopes": auth.SCOPE.split()})
        rows = api_model_preflight({"models": config}, require_credentials=True)
        self.assertTrue(rows["planner"]["credential_configured"])
        _, _, models = model_configuration(models=config)
        self.assertEqual(
            models["online_critic"]["factory"],
            "vlm.chatgpt_subscription:ChatGPTSubscriptionVisionModel",
        )

    def test_durable_call_reuses_answer_without_second_dispatch(self):
        from planner_harness.model_call import metered_text

        client = ChatGPTSubscriptionVisionModel()
        with patch(
            "vlm.chatgpt_subscription.urllib.request.urlopen", return_value=stream(complete())
        ) as post:
            first = metered_text(self.root / "call", client, "s", "u", [])
            second = metered_text(self.root / "call", client, "s", "u", [])
        self.assertEqual(first, second)
        post.assert_called_once()
        result = json.loads((self.root / "call/attempts/01/result.json").read_text())
        self.assertEqual(result["usage"]["total_tokens"], 16)

    def test_relay_real_http_keeps_body_and_credentials_at_single_owner(self):
        from vlm.chatgpt_relay import make_server

        response = stream(complete())
        response.status = 200
        response.headers = {"Content-Type": "application/json"}
        with make_server(0, str(self.path)) as server:
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                with (
                    patch(
                        "vlm.chatgpt_relay.access_token", return_value="relay-owner-secret"
                    ) as token,
                    patch("vlm.chatgpt_relay.open_upstream", return_value=response) as upstream,
                ):
                    model = ChatGPTSubscriptionVisionModel(
                        relay_url=f"http://127.0.0.1:{server.server_address[1]}"
                    )
                    answer = model.predict_json(
                        system_prompt="same instructions", user_text="x" * 167902, image_paths=[]
                    )
                    self.assertEqual(answer, {"ok": True})
                token.assert_called_once_with(str(self.path))
                request = upstream.call_args.args[0]
                self.assertEqual(request.get_header("Authorization"), "Bearer relay-owner-secret")
                self.assertEqual(request.full_url, auth.RESOURCE + "/responses")
                from vlm.response_contract import INSTRUCTION
                self.assertEqual(json.loads(request.data)["instructions"], "same instructions\n\n" + INSTRUCTION)
                self.assertEqual(
                    len(json.loads(request.data)["input"][0]["content"][0]["text"]), 167902
                )
                self.assertNotIn("relay-owner-secret", json.dumps(model.last_client_audit))
            finally:
                server.shutdown()
                worker.join()

    def test_relay_interrupted_upstream_stays_unknown(self):
        from vlm.chatgpt_relay import make_server

        with make_server(0, str(self.path)) as server:
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                with (
                    patch("vlm.chatgpt_relay.access_token", return_value="fixture"),
                    patch("vlm.chatgpt_relay.open_upstream", side_effect=ConnectionResetError()),
                ):
                    model = ChatGPTSubscriptionVisionModel(
                        relay_url=f"http://127.0.0.1:{server.server_address[1]}"
                    )
                    with self.assertRaises(ExternalExecutionUnknown):
                        model.predict_text(system_prompt="s", user_text="u", image_paths=[])
            finally:
                server.shutdown()
                worker.join()

    def test_relay_workers_configure_without_local_oauth_file(self):
        from experiments.preflight import api_model_preflight

        config = json.loads((ROOT / "configs/chatgpt-subscription-models.json").read_text())
        for spec in config.values():
            spec["options"].update(
                relay_url="http://127.0.0.1:18766", credential_file=str(self.path)
            )
        rows = api_model_preflight({"models": config}, require_credentials=True)
        self.assertTrue(rows["online_critic"]["credential_configured"])
        self.assertFalse(self.path.exists())


if __name__ == "__main__":
    unittest.main()
