"""Authored loopback Gateway double, never a live model or external integration."""
from http.server import BaseHTTPRequestHandler, HTTPServer
import hashlib
import threading
import uuid
from .gateway import canonical, strict

MODEL = "local/synthetic-tool-double"

def envelope(generation, *, tool=None, arguments=None, final=None):
    message = {"role": "assistant", "content": final}
    if tool:
        message["tool_calls"] = [{"id": "call-"+generation, "type": "function",
            "function": {"name": tool, "arguments": canonical(arguments).decode()}}]
    return {"id": "chat-"+generation, "object": "chat.completion", "model": MODEL,
            "choices": [{"index": 0, "finish_reason": "tool_calls" if tool else "stop", "message": message}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}

def decide(body, generation):
    request, state, seen = None, {}, set()
    for message in body["messages"]:
        if message["role"] == "user":
            value = strict(message["content"])
            if "resume_snapshot" in value: state = value["resume_snapshot"]
            elif "employee_id" in value: request = value
        elif message["role"] == "assistant":
            for call in message.get("tool_calls", []): seen.add(call["function"]["name"])
        elif message["role"] == "tool":
            value = strict(message["content"])
            if "administrative_status" in value: state = value
    if request is None: raise ValueError("double requires explicit request")
    if "inspect_employee" not in seen:
        return envelope(generation, tool="inspect_employee", arguments={"employee_id": request["employee_id"]})
    if "read_policy" not in seen:
        return envelope(generation, tool="read_policy", arguments={"policy_id": "offboarding-v1"})
    if not state.get("digest"):
        return envelope(generation, tool="propose_plan", arguments={"employee_id": request["employee_id"], "intent": request["intent"]})
    if state.get("administrative_status") in {"RUNNING", "RETRY_PENDING"} and state.get("eligible_step"):
        return envelope(generation, tool="execute_step", arguments={"workflow_id": state["workflow_id"], "step_id": state["eligible_step"]})
    return envelope(generation, final="Completed." if state.get("administrative_status") == "COMPLETED" else "Operator review required.")

class LocalDouble:
    """Owns one socket and one server thread. Caller must use the context manager."""
    def __init__(self, respond=None, *, trickle=False):
        self.respond, self.requests, self.cleanup = respond, [], None
        self.trickle = trickle
        self.request_received = threading.Event(); self.response_started = threading.Event()
        self.abort = threading.Event(); self.prefix = uuid.uuid4().hex[:12]
    def __enter__(self):
        owner = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_): pass
            def do_POST(self):
                size = int(self.headers.get("Content-Length", "0"))
                if self.path != "/v1/chat/completions" or not 0 < size <= 131072:
                    self.send_error(400); return
                raw = self.rfile.read(size); body = strict(raw)
                owner.requests.append({"request_sha256": hashlib.sha256(raw).hexdigest(),
                    "authorization_present": "Authorization" in self.headers, "model": body.get("model")})
                owner.request_received.set()
                generation = owner.prefix+"-"+str(len(owner.requests))
                result = owner.respond(body, generation, owner.abort) if owner.respond else decide(body, generation)
                if result is None:
                    self.close_connection = True; return
                if isinstance(result, tuple):
                    status, payload, *extra = result
                    headers = extra[0] if extra else {}
                else: status, payload, headers = 200, canonical(result), {}
                self.send_response(status); self.send_header("Content-Type", headers.get("Content-Type", "application/json"))
                for key, value in headers.items():
                    if key != "Content-Type": self.send_header(key, value)
                self.send_header("Content-Length", str(len(payload))); self.end_headers()
                try:
                    if owner.trickle:
                        self.wfile.write(payload[:1]); self.wfile.flush(); owner.response_started.set(); owner.abort.wait(30)
                        self.wfile.write(payload[1:])
                    else: self.wfile.write(payload)
                except (BrokenPipeError, ConnectionResetError): pass
        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.server.timeout = .1
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": .05}, daemon=True)
        self.thread.start()
        self.endpoint = "http://127.0.0.1:"+str(self.server.server_port)+"/v1/chat/completions"
        return self
    def __exit__(self, *_):
        self.abort.set(); self.server.shutdown(); self.server.server_close(); self.thread.join(timeout=1)
        self.cleanup = {"server_thread_live": self.thread.is_alive(), "socket_closed": self.server.socket.fileno() == -1}
        if self.cleanup["server_thread_live"] or not self.cleanup["socket_closed"]:
            raise RuntimeError("DOUBLE_CLEANUP_UNCONFIRMED")
