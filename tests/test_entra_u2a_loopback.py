"""UNEXECUTED/LEASE REQUIRED: four literal-loopback read-only Entra contract cells."""
import contextlib
import http.client
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import tempfile
import threading
import time
import unittest
from urllib.parse import urlsplit
from agent.bridge import ROOT
from agent.entra_contract import EntraAdapter, EntraError, IntentJournal, ORIGIN, Reply, request_for
from tests.entra_fixtures import PROFILE, TENANT, USER, FakeGraph, approval, attestation, authority, response

class LoopbackReader:
    kind = "injected-double"
    def __init__(self, port): self.port = port
    def read(self, request, deadline):
        if request["method"] != "GET": raise AssertionError("Mutation transport disabled")
        url = urlsplit(request["url"]); remaining = deadline-time.monotonic()
        if remaining <= 0: raise TimeoutError()
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=min(.2, remaining))
        try:
            connection.request("GET", url.path+"?"+url.query)
            reply = connection.getresponse(); body = bytearray()
            while len(body) <= 65536:
                remaining = deadline-time.monotonic()
                if remaining <= 0: raise TimeoutError()
                if connection.sock: connection.sock.settimeout(min(.2, remaining))
                part = reply.read(1)
                if not part: break
                body.extend(part)
            return Reply(reply.status, bytes(body), {"Content-Type": reply.getheader("Content-Type", "")})
        finally: connection.close()

@contextlib.contextmanager
def server(graph):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_GET(self):
            result = graph.read({"method": "GET", "url": "https://graph.microsoft.com"+self.path, "body": None}, time.monotonic()+5)
            self.send_response(result.status); self.send_header("Content-Type", result.headers.get("Content-Type", "application/json"))
            self.send_header("Content-Length", str(len(result.body))); self.end_headers()
            try: self.wfile.write(result.body)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError): pass
    listener = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=listener.serve_forever, kwargs={"poll_interval": .02}, daemon=True); thread.start()
    try: yield LoopbackReader(listener.server_port)
    finally:
        listener.shutdown(); listener.server_close(); thread.join(timeout=1)
        if thread.is_alive(): raise AssertionError("Owned loopback server thread remains live")

class EntraLoopback(unittest.TestCase):
    def setUp(self):
        (ROOT/"work").mkdir(exist_ok=True)
        folder = tempfile.TemporaryDirectory(prefix="u2a-loopback-", dir=ROOT/"work"); self.addCleanup(folder.cleanup)
        self.journal = IntentJournal(Path(folder.name)/"intents.json", PROFILE, "wf-fictional")
        self.graph = FakeGraph()
    def adapter(self, reader, **kwargs):
        return EntraAdapter(PROFILE, self.journal, attestation(), authority, reader=reader, wall_clock=lambda: 1000, **kwargs)
    def test_loopback_intake_and_unconditional_mutation_gate(self):
        with server(self.graph) as reader:
            adapter = self.adapter(reader); facts = adapter.intake("E-104")
            req = request_for(PROFILE, USER, "disable"); record = adapter.prepare(facts, "disable", approval(facts, req))
            count = len(self.graph.requests)
            with self.assertRaisesRegex(EntraError, "REMOTE_DISPATCH_DISABLED"): adapter.dispatch(record["id"])
            self.assertEqual(len(self.graph.requests), count)
        self.assertTrue(all(r["method"] == "GET" for r in self.graph.requests))
    def test_loopback_cross_host_nextlink_never_followed(self):
        self.graph.override = lambda r: response({"value": [], "@odata.nextLink": "https://elsewhere.invalid/v1.0/users"}) if "/memberOf?" in r["url"] else None
        with server(self.graph) as reader:
            with self.assertRaisesRegex(EntraError, "GRAPH_ORIGIN"): self.adapter(reader).intake("E-104")
        self.assertEqual(len(self.graph.requests), 3)
    def test_loopback_reserved_lost_reply_readback_without_post(self):
        with server(self.graph) as reader:
            adapter = self.adapter(reader); facts = adapter.intake("E-104")
            req = request_for(PROFILE, USER, "revoke"); grant = approval(facts, req)
            record = adapter.prepare(facts, "revoke", grant); adapter.reserve_contract_attempt(record["id"], grant)
            self.assertEqual(adapter.reconcile(record["id"])["phase"], "UNCERTAIN")
            self.graph.user["signInSessionsValidFromDateTime"] = "2026-10-12T07:00:00Z"
            self.assertTrue(adapter.reconcile(record["id"])["postcondition_observed"])
            with self.assertRaisesRegex(EntraError, "ALREADY_RESERVED"): adapter.reserve_contract_attempt(record["id"], grant)
        self.assertTrue(all(r["method"] == "GET" for r in self.graph.requests))
    def test_loopback_read_deadline_is_bounded(self):
        def slow(_): time.sleep(.35); return response({"value": [{"id": TENANT}]})
        self.graph.override = slow; start = time.monotonic()
        with server(self.graph) as reader:
            adapter = self.adapter(reader, deadline=time.monotonic()+.1)
            with self.assertRaises(EntraError): adapter.intake("E-104")
            self.assertLess(time.monotonic()-start, .3)
        self.assertLess(time.monotonic()-start, 1)

if __name__ == "__main__": unittest.main()
