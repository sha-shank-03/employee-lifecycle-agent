"""Bounded child-process RPC. Actor and operator modes are separate launches."""
from pathlib import Path
import os
import queue
import re
import shutil
import struct
import subprocess
import threading
from .protocol import MAX_FRAME, decode_response, encode_request, validate_call

ROOT = Path(__file__).resolve().parents[1]


def java_executable(name="java") -> str:
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        candidate = Path(java_home) / "bin" / (name + (".exe" if os.name == "nt" else ""))
        if candidate.is_file():
            return str(candidate)
    found = shutil.which(name)
    if not found:
        raise RuntimeError(f"{name} unavailable; install/select a Java 17 JDK separately")
    return found


class BridgeError(RuntimeError):
    pass


class JavaBridge:
    def __init__(self, run_dir, *, mode="actor", crash_after=None):
        if mode not in {"actor", "operator"}:
            raise ValueError("invalid process mode")
        classes = ROOT / ".build" / "classes"
        if not (classes / "lifecycle" / "Main.class").exists():
            raise BridgeError("Java build absent; run py -3.11 dev.py build")
        command = [java_executable(), "-Xmx256m", "-cp", str(classes), "lifecycle.Main",
                   "--run-dir", str(Path(run_dir).resolve()), "--mode", mode]
        if crash_after is not None:
            if crash_after != "disable_login" and not re.fullmatch(r"(before_intent|after_intent|after_service_commit|after_result):(disable_login|add_role_grants|create_collection_task|undo_role_grants)", crash_after):
                raise ValueError("unknown finite crash hook")
            command += ["--crash-after", crash_after]
        self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, bufsize=0)
        self.responses = queue.Queue()
        self.diagnostics = bytearray()
        self.counter = 0
        self.reader = threading.Thread(target=self._read_responses, daemon=True)
        self.error_reader = threading.Thread(target=self._read_stderr, daemon=True)
        self.reader.start()
        self.error_reader.start()

    def _exact(self, count):
        result = bytearray()
        while len(result) < count:
            chunk = self.process.stdout.read(count - len(result))
            if not chunk:
                raise EOFError("Java response ended before acknowledgement")
            result.extend(chunk)
        return bytes(result)

    def _read_responses(self):
        try:
            while True:
                size = struct.unpack(">I", self._exact(4))[0]
                if size > MAX_FRAME or size == 0:
                    raise ValueError("invalid response frame length")
                self.responses.put(self._exact(size))
        except Exception as error:
            self.responses.put(error)

    def _read_stderr(self):
        while chunk := self.process.stderr.read(1024):
            remaining = 8192 - len(self.diagnostics)
            if remaining > 0:
                self.diagnostics.extend(chunk[:remaining])

    def request(self, fields):
        self.counter += 1
        request_id = str(self.counter)
        try:
            self.process.stdin.write(encode_request(request_id, fields))
            self.process.stdin.flush()
            response = self.responses.get(timeout=5)
            if isinstance(response, Exception):
                raise response
            return decode_response(response, request_id)
        except Exception as error:
            self.close()
            raise BridgeError(f"Java RPC failed; reconcile persisted receipts on restart: {error}") from error

    def call(self, call):
        validate_call(call)
        return self.request({"tool": call.name, **call.arguments})

    def begin_turn(self):
        return self.request({"tool": "begin_turn"})

    def charge_wait(self, milliseconds):
        return self.request({"tool": "charge_wait", "milliseconds": str(milliseconds)})

    def stop_actor(self, workflow, reason):
        return self.request({"tool": "stop_actor", "workflow_id": workflow, "reason_code": reason})

    def close(self):
        if self.process.stdin and not self.process.stdin.closed:
            try:
                self.process.stdin.close()
            except OSError:
                pass
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=2)
        self.reader.join(timeout=0.5)
        self.error_reader.join(timeout=0.5)
        for stream in (self.process.stdout, self.process.stderr):
            if stream:
                stream.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
