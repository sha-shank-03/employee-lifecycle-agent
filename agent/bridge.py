"""Bounded child-process RPC. Actor and operator modes are separate launches."""
from pathlib import Path
import os
import queue
import re
import shutil
import struct
import subprocess
import threading
import time
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
    def __init__(self, run_dir, *, mode="actor", crash_after=None, deadline=None, cancel=None):
        self.deadline, self.cancel, self.cleanup = deadline, cancel, None
        if deadline is not None and deadline-time.monotonic() <= 2:
            raise BridgeError("OWNED_DEADLINE_PREFLIGHT")
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
        self.started_ns = time.monotonic_ns()
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

    def request(self, fields, *, timeout=5, allow_cancel=False, deadline=None):
        self.counter += 1
        request_id = str(self.counter)
        try:
            frame = encode_request(request_id, fields)
            end = time.monotonic() + timeout
            if self.deadline is not None:
                end = min(end, self.deadline - 1.5)
            if deadline is not None:
                end = min(end, deadline)
            if time.monotonic() >= end or not allow_cancel and self.cancel is not None and self.cancel.is_set():
                raise TimeoutError("RPC_CANCELLED_OR_DEADLINE")
            self.process.stdin.write(frame)
            self.process.stdin.flush()
            while True:
                if (not allow_cancel and self.cancel is not None and self.cancel.is_set()) or time.monotonic() >= end:
                    raise TimeoutError("RPC_CANCELLED_OR_DEADLINE")
                try:
                    response = self.responses.get(timeout=min(.05, max(.001, end-time.monotonic())))
                    break
                except queue.Empty:
                    continue
            if isinstance(response, Exception):
                raise response
            return decode_response(response, request_id)
        except Exception as error:
            self.close(force=self.deadline is not None)
            if self.deadline is not None:
                raise BridgeError("JAVA_REPLY_UNCERTAIN") from None
            raise BridgeError(f"Java RPC failed; reconcile persisted receipts on restart: {error}") from error

    def call(self, call):
        validate_call(call)
        return self.request({"tool": call.name, **call.arguments})

    def begin_turn(self):
        return self.request({"tool": "begin_turn"})

    def charge_wait(self, milliseconds):
        return self.request({"tool": "charge_wait", "milliseconds": str(milliseconds)})

    def stop_actor(self, workflow, reason, *, timeout=5):
        return self.request({"tool": "stop_actor", "workflow_id": workflow, "reason_code": reason}, timeout=timeout, allow_cancel=True)

    def close(self, *, force=False):
        if self.cleanup is not None:
            return
        def remaining(limit):
            return limit if self.deadline is None else max(.001, min(limit, self.deadline-time.monotonic()))
        if force and self.process.poll() is None:
            self.process.kill()
        if self.process.stdin and not self.process.stdin.closed:
            try:
                self.process.stdin.close()
            except OSError:
                pass
        try:
            self.process.wait(timeout=remaining(5 if self.deadline is None else .5))
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=remaining(2 if self.deadline is None else .5))
        self.reader.join(timeout=remaining(0.25 if self.deadline is not None else .5))
        self.error_reader.join(timeout=remaining(0.25 if self.deadline is not None else .5))
        for stream in (self.process.stdout, self.process.stderr):
            if stream:
                stream.close()
        self.cleanup = {"owned_pid": self.process.pid, "exit_code": self.process.returncode,
                        "started_monotonic_ns": self.started_ns,
                        "live": self.process.poll() is None,
                        "reader_live": self.reader.is_alive(), "stderr_reader_live": self.error_reader.is_alive()}
        if any(self.cleanup[k] for k in ("live", "reader_live", "stderr_reader_live")):
            raise BridgeError("OWNED_CLEANUP_UNCONFIRMED")

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
