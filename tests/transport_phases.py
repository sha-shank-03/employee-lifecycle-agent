"""Leased test fixtures, never a provider API or a replacement HTTP reply.

Preparation owns one real gateway_worker and one real HTTP attempt. The response
timer starts only after server evidence confirms the selected phase; preparation
has its own five-second deadline and unconditional bounded child cleanup.
"""
import base64
import hashlib
from pathlib import Path
import subprocess
import sys
import time
from agent.gateway import OwnedDoubleExchange, _transport_environment, canonical

WORKER = Path(__file__).resolve().parents[1]/"agent/gateway_worker.py"
STARTUP_HOLD = "import sys,time,runpy;time.sleep(30);runpy.run_path(sys.argv[1],run_name='__main__')"

def worker_arguments(): return [sys.executable,str(WORKER)]

def require_worker(arguments, options):
    if arguments != worker_arguments() or set(options) != {"stdin","stdout","stderr","env"} \
            or any(options[n] != subprocess.PIPE for n in ("stdin","stdout","stderr")):
        raise AssertionError("fixed owned worker launch required")

def held_startup_factory(launch):
    """Native cold-start fixture: delay before the actual unchanged worker runs."""
    def held(arguments, **options):
        require_worker(arguments,options)
        return launch([sys.executable,"-c",STARTUP_HOLD,str(WORKER)],**options)
    return held

def confirmed_phase(double, body, phase):
    if phase not in {"stalled-response","trickled-body"}:
        raise ValueError("known response phase required")
    if len(double.requests) != 1 or double.requests[0]["request_sha256"] != hashlib.sha256(body).hexdigest():
        raise AssertionError("exactly one matching real dispatch required")
    if not double.request_received.is_set(): raise AssertionError("request receipt unconfirmed")
    if phase == "trickled-body" and not double.response_started.is_set():
        raise AssertionError("first response byte unconfirmed")

class DispatchedAttempt:
    """Test-only ownership seam for an already confirmed, still-running attempt.

    Popen is intercepted only at adoption. The real worker received the identical
    canonical payload once during preparation; communicate afterwards sends no
    further input and reads the actual worker pipes. No retry/response fabrication.
    """
    def __init__(self, double, body, *, phase, launch=None):
        OwnedDoubleExchange(double.endpoint)  # Retain the same literal-loopback gate.
        if len(body)>131072: raise ValueError("bounded body required")
        if phase not in {"stalled-response","trickled-body"}: raise ValueError("known response phase required")
        self.double,self.body,self.phase = double,body,phase
        self.launch = launch or subprocess.Popen
        self.payload = canonical({"endpoint":double.endpoint,"body":base64.b64encode(body).decode()})
        self.process = None; self.claimed = False; self.input_consumed = False; self.reaped = False
        self.preparation_seconds = None
    def __enter__(self):
        started = time.monotonic(); self.started_ns = time.monotonic_ns(); deadline = started+5
        self.environment = _transport_environment()
        try:
            self.process = self.launch(worker_arguments(),stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,env=self.environment)
            try:
                self.process.communicate(input=self.payload,timeout=min(.05,max(.001,deadline-time.monotonic())))
            except subprocess.TimeoutExpired:
                pass
            else:
                raise AssertionError("phase fixture must remain in flight")
            signal = self.double.response_started if self.phase=="trickled-body" else self.double.request_received
            if not signal.wait(max(0,deadline-time.monotonic())):
                raise TimeoutError("five-second preparation phase unconfirmed")
            if time.monotonic()>=deadline: raise TimeoutError("preparation deadline exceeded")
            confirmed_phase(self.double,self.body,self.phase)
            if self.process.poll() is not None: raise AssertionError("confirmed child no longer in flight")
            self.preparation_seconds = time.monotonic()-started
            return self
        except BaseException:
            self.close(); raise
    def claim(self, arguments, **options):
        require_worker(arguments,options)
        if options["env"] != self.environment or self.claimed or self.process is None:
            raise AssertionError("single matching prepared worker adoption required")
        confirmed_phase(self.double,self.body,self.phase)
        self.claimed = True
        return self
    def communicate(self, input=None, timeout=None):
        if input is not None:
            if input != self.payload or self.input_consumed: raise AssertionError("prepared payload mismatch or resend")
            self.input_consumed = True
        result = self.process.communicate(timeout=timeout)
        self.reaped = self.process.poll() is not None
        return result
    @property
    def pid(self): return self.process.pid
    @property
    def returncode(self): return self.process.returncode
    def poll(self): return self.process.poll()
    def kill(self): return self.process.kill()
    def close(self):
        if self.process is None or self.reaped: return
        if self.process.poll() is None: self.process.kill()
        self.process.communicate(timeout=1.5)
        if self.process.poll() is None: raise AssertionError("phase fixture owned cleanup unconfirmed")
        self.reaped = True
    def observation(self):
        return {"mode":"local-double","phase":self.phase,"confirmed_requests":len(self.double.requests),
            "response_first_byte_confirmed":self.double.response_started.is_set(),
            "startup_included_in_response_timer":False,"preparation_cap_seconds":5,
            "preparation_seconds":self.preparation_seconds,"fixture_cleanup_cap_seconds":1.5,
            "owned_pid":self.pid,"fixture_start_monotonic_ns":self.started_ns,
            "parent_cleanup_start_is_adoption_time":True,"automatic_retries":0}
    def __exit__(self,*_): self.close()
