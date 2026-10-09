"""LEASE REQUIRED: actual credential-free loopback HTTP; never a model endpoint."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import time
import unittest
from agent.protocol import FinalDraft, ToolCall
from agent.responses import HttpTransport, ProviderError, ResponsesProvider, canonical
from tests.test_provider_unit import REQUEST, function_response, message_response


class LocalHTTPContracts(unittest.TestCase):
    def setUp(self):
        self.requests, self.replies = [], []
        parent = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_POST(self):
                size = int(self.headers.get("Content-Length", "0"))
                parent.requests.append({"path": self.path, "body": json.loads(self.rfile.read(size)),
                                        "authorization": self.headers.get("Authorization")})
                status, body, content_type, delay = parent.replies.pop(0)
                if delay:
                    time.sleep(delay)
                try:
                    self.send_response(status)
                    self.send_header("Content-Type", content_type)
                    self.send_header("Content-Length", str(len(body)))
                    if status == 302:
                        self.send_header("Location", "/should-not-follow")
                    self.end_headers()
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = False  # server_close also joins bounded request handlers
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.02})
        self.thread.start()
        self.addCleanup(self.close_server)
        endpoint = f"http://127.0.0.1:{self.server.server_port}/v1/responses"
        self.provider = ResponsesProvider("synthetic-protocol-model", HttpTransport(endpoint, loopback_test=True))

    def close_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        self.assertFalse(self.thread.is_alive())

    def reply(self, value, status=200, content_type="application/json", delay=0):
        self.replies.append((status, canonical(value), content_type, delay))

    def test_wire_function_call_and_result_correlation(self):
        self.reply(function_response())
        self.reply(message_response())
        call = self.provider.next_turn(REQUEST, [])
        self.assertIsInstance(call, ToolCall)
        decision = self.provider.next_turn(REQUEST, [{"tool": call.name, "arguments": call.arguments, "result": {"code": "OK"}}])
        self.assertIsInstance(decision, FinalDraft)
        self.assertEqual(self.requests[1]["body"]["input"][-1]["call_id"], "call_1")
        self.assertEqual([r["authorization"] for r in self.requests], [None, None])
        self.assertEqual([r["path"] for r in self.requests], ["/v1/responses"] * 2)

    def test_429_fails_once_without_retry(self):
        self.reply({"error": "synthetic"}, status=429)
        with self.assertRaisesRegex(ProviderError, "429"):
            self.provider.next_turn(REQUEST, [])
        self.assertEqual(len(self.requests), 1)

    def test_500_fails_once_without_retry(self):
        self.reply({"error": "synthetic"}, status=500)
        with self.assertRaisesRegex(ProviderError, "500"):
            self.provider.next_turn(REQUEST, [])
        self.assertEqual(len(self.requests), 1)

    def test_redirect_is_not_followed(self):
        self.reply({}, status=302)
        with self.assertRaisesRegex(ProviderError, "302"):
            self.provider.next_turn(REQUEST, [])
        self.assertEqual(len(self.requests), 1)

    def test_wrong_content_type_is_rejected(self):
        self.reply(function_response(), content_type="text/plain")
        with self.assertRaisesRegex(ProviderError, "content type"):
            self.provider.next_turn(REQUEST, [])

    def test_response_body_is_bounded(self):
        self.reply({"oversized": "x" * 70_000})
        with self.assertRaisesRegex(ProviderError, "64 KiB"):
            self.provider.next_turn(REQUEST, [])

    def test_socket_timeout_is_a_bounded_stop(self):
        self.reply(function_response(), delay=2)
        started = time.monotonic()
        with self.assertRaises(TimeoutError):
            self.provider.next_turn(REQUEST, [])
        self.assertLess(time.monotonic() - started, 3)
        self.assertEqual(len(self.requests), 1)


if __name__ == "__main__":
    unittest.main()
