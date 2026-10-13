"""U2-A injected offboarding contract. No HTTP implementation or credential loader."""
import copy
from dataclasses import asdict, dataclass
from datetime import datetime
import math
import os
from pathlib import Path
import re
import threading
import time
from typing import Protocol
from urllib.parse import parse_qsl, urlsplit
from uuid import UUID
from .gateway import canonical, digest, strict

VERSION = "entra-u2a-contract-1"
ORIGIN = "https://graph.microsoft.com/v1.0"
PERMISSIONS = {"User.Read.All", "User.EnableDisableAccount.All", "User.RevokeSessions.All",
               "GroupMember.ReadWrite.All", "Directory.Read.All"}
USER_SELECT = "id,accountEnabled,userType,onPremisesSyncEnabled,signInSessionsValidFromDateTime"
GROUP_SELECT = "id,groupTypes,securityEnabled,mailEnabled,isAssignableToRole,membershipRule,onPremisesSyncEnabled"
MAX_CALLS, MAX_REPLY, MAX_PAGES = 40, 65536, 3

class EntraError(ValueError):
    """Only fixed diagnostics leave the adapter; raw Graph errors are not logged."""

def require(condition, code):
    if not condition: raise EntraError(code)

def guid(value):
    try:
        require(type(value) is str and str(UUID(value)) == value, "INVALID_OBJECT_ID")
    except (ValueError, TypeError, AttributeError):
        raise EntraError("INVALID_OBJECT_ID") from None
    return value

def stamp(value):
    require(type(value) is str and re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,7})?Z", value), "INVALID_CUTOFF")
    try: return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError: raise EntraError("INVALID_CUTOFF") from None

def exact(value, fields, code, optional=()):
    require(type(value) is dict and set(fields) <= set(value) <= set(fields) | set(optional), code)
    for key in set(value) & set(optional):
        if key.startswith("@odata"):
            require(type(value[key]) is str and len(value[key]) <= 2048, code)

def profile(value):
    exact(value, {"schema", "version", "mode", "tenant_id", "app_id", "users", "groups", "remote_dispatch"}, "INVALID_PROFILE")
    require(type(value["schema"]) is int and value["schema"] == 1 and value["version"] == VERSION
            and value["mode"] == "injected-double" and value["remote_dispatch"] is False, "REMOTE_PROFILE_DENIED")
    guid(value["tenant_id"]); guid(value["app_id"])
    require(type(value["users"]) is dict and 1 <= len(value["users"]) <= 4, "INVALID_USER_ALLOWLIST")
    for employee, user in value["users"].items():
        require(type(employee) is str and re.fullmatch(r"E-\d{3,6}", employee), "INVALID_EMPLOYEE_MAPPING"); guid(user)
    require(len(set(value["users"].values())) == len(value["users"]), "INVALID_USER_ALLOWLIST")
    require(type(value["groups"]) is list and 1 <= len(value["groups"]) <= 2
            and all(type(g) is str for g in value["groups"])
            and value["groups"] == sorted(set(value["groups"])), "INVALID_GROUP_ALLOWLIST")
    for group in value["groups"]: guid(group)
    return copy.deepcopy(value)

@dataclass(frozen=True)
class TrustedAttestation:
    """Supplied by trusted main preflight, NEVER by decoded bearer-token claims."""
    profile_sha256: str
    tenant_id: str
    app_id: str
    non_admin_users: tuple
    isolated: bool
    permissions: tuple
    expires_at: float

@dataclass(frozen=True)
class TrustedApproval:
    """Host authority must verify the proof; a digest or this type alone is not approval."""
    workflow: str
    profile_sha256: str
    facts_sha256: str
    request_sha256: str
    expires_at: float
    proof_ref: str

class TokenLoader(Protocol):
    """Main supplies a future loader. U2-A never calls it or inspects a token."""
    def load(self, tenant_id: str, app_id: str, authority: str, scope: str) -> str: ...

@dataclass(frozen=True)
class Reply:
    status: int
    body: bytes
    headers: dict

class DisabledReader:
    kind = "disabled"
    def read(self, request, deadline): raise EntraError("REMOTE_DISPATCH_DISABLED")

def request_for(p, user, action, group=None):
    require(user in p["users"].values(), "USER_NOT_ALLOWED")
    if action == "disable":
        require(group is None, "UNEXPECTED_GROUP"); method, path, body = "PATCH", "/users/"+user, {"accountEnabled": False}
    elif action == "revoke":
        require(group is None, "UNEXPECTED_GROUP"); method, path, body = "POST", "/users/"+user+"/revokeSignInSessions", None
    elif action == "remove_membership":
        require(group in p["groups"], "GROUP_NOT_ALLOWED")
        method, path, body = "DELETE", "/groups/"+group+"/members/"+user+"/$ref", None
    else: raise EntraError("ACTION_NOT_ALLOWED")
    return {"method": method, "url": ORIGIN+path, "body": body}

def validate_request(p, request):
    exact(request, {"method", "url", "body"}, "INVALID_REQUEST")
    require(type(request["url"]) is str and len(request["url"]) <= 2048 and not re.search(r"[\x00-\x20]", request["url"]), "INVALID_URL")
    try: url = urlsplit(request["url"])
    except ValueError: raise EntraError("INVALID_URL") from None
    require(url.scheme == "https" and url.netloc == "graph.microsoft.com" and not url.fragment, "GRAPH_ORIGIN_REQUIRED")
    if request["method"] != "GET":
        if request["method"] == "PATCH":
            require(type(request["body"]) is dict and set(request["body"]) == {"accountEnabled"}
                    and request["body"]["accountEnabled"] is False, "MUTATION_ROUTE_OR_PAYLOAD_DENIED")
        for user in p["users"].values():
            for action, group in [("disable", None), ("revoke", None)] + [("remove_membership", g) for g in p["groups"]]:
                if request == request_for(p, user, action, group): return
        raise EntraError("MUTATION_ROUTE_OR_PAYLOAD_DENIED")
    require(request["body"] is None, "GET_BODY_DENIED")
    fixed = {ORIGIN+"/organization?$select=id"}
    fixed.update(ORIGIN+"/users/"+u+"?$select="+USER_SELECT for u in p["users"].values())
    fixed.update(ORIGIN+"/groups/"+g+"?$select="+GROUP_SELECT for g in p["groups"])
    if request["url"] in fixed: return
    require(url.path in {"/v1.0/users/"+u+"/memberOf" for u in p["users"].values()}, "READ_ROUTE_DENIED")
    try: query = parse_qsl(url.query, keep_blank_values=True, strict_parsing=True)
    except ValueError: raise EntraError("PAGINATION_QUERY_DENIED") from None
    require(len(query) == len(dict(query)) and {"$select", "$top"} <= set(dict(query))
            <= {"$select", "$top", "$skiptoken", "$skip"}, "PAGINATION_QUERY_DENIED")
    values = dict(query)
    require(values["$select"] == "id" and values["$top"] == "20"
            and all(0 < len(v) <= 1024 for v in values.values()), "PAGINATION_QUERY_DENIED")
    require(not ({"$skip", "$skiptoken"} <= set(values)), "PAGINATION_QUERY_DENIED")
    if "$skip" in values: require(values["$skip"].isdigit(), "PAGINATION_QUERY_DENIED")

def user_facts(value, user):
    exact(value, USER_SELECT.split(","), "USER_SCHEMA", ("@odata.context", "@odata.type"))
    require(value["id"] == user and value.get("@odata.type", "#microsoft.graph.user") == "#microsoft.graph.user", "USER_ID_OR_TYPE")
    require(type(value["accountEnabled"]) is bool and value["userType"] == "Member", "UNSUPPORTED_USER")
    require(value["onPremisesSyncEnabled"] is None or value["onPremisesSyncEnabled"] is False, "SYNCED_USER_DENIED")
    stamp(value["signInSessionsValidFromDateTime"])
    return {k: value[k] for k in USER_SELECT.split(",")}

def group_facts(value, group):
    exact(value, GROUP_SELECT.split(","), "GROUP_SCHEMA", ("@odata.context", "@odata.type"))
    require(value["id"] == group and value.get("@odata.type", "#microsoft.graph.group") == "#microsoft.graph.group", "GROUP_ID_OR_TYPE")
    require(value["groupTypes"] == [] and type(value["groupTypes"]) is list
            and value["securityEnabled"] is True and value["mailEnabled"] is False
            and value["isAssignableToRole"] is False and value["membershipRule"] is None
            and (value["onPremisesSyncEnabled"] is None or value["onPremisesSyncEnabled"] is False), "UNSUPPORTED_GROUP")
    return {k: value[k] for k in GROUP_SELECT.split(",")}

def validate_facts(p, value):
    exact(value, {"tenant_id", "employee_id", "user", "members", "groups"}, "FACTS_SCHEMA")
    require(value["tenant_id"] == p["tenant_id"] and type(value["employee_id"]) is str
            and value["employee_id"] in p["users"], "FACTS_PROFILE_DRIFT")
    user_facts(value["user"], p["users"][value["employee_id"]])
    require(type(value["members"]) is list and all(type(i) is str for i in value["members"])
            and value["members"] == sorted(set(value["members"])) and set(value["members"]) <= set(p["groups"]), "FACTS_MEMBERSHIP")
    require(type(value["groups"]) is list and len(value["groups"]) == len(p["groups"]), "FACTS_GROUPS")
    for group, expected in zip(value["groups"], p["groups"]): group_facts(group, expected)

class IntentJournal:
    """One trusted writer, atomic replacement; not a distributed/Java outbox or power-loss guarantee."""
    def __init__(self, path, p, workflow):
        require(type(workflow) is str and re.fullmatch(r"[A-Za-z0-9_-]{1,80}", workflow), "INVALID_WORKFLOW")
        self.path, self.profile, self.workflow = Path(path), profile(p), workflow
        self.lock = threading.RLock()
        if self.path.exists():
            require(self.path.stat().st_size <= 65536, "JOURNAL_TOO_LARGE")
            try: self.state = strict(self.path.read_bytes())
            except ValueError: raise EntraError("INVALID_JOURNAL") from None
        else:
            self.state = {"schema": 1, "version": VERSION, "profile_sha256": digest(self.profile), "workflow": workflow, "calls": 0, "intents": {}}
        exact(self.state, {"schema", "version", "profile_sha256", "workflow", "calls", "intents"}, "INVALID_JOURNAL")
        require(self.state["schema"] == 1 and type(self.state["schema"]) is int and self.state["version"] == VERSION
                and self.state["profile_sha256"] == digest(self.profile) and self.state["workflow"] == workflow, "PROFILE_OR_WORKFLOW_DRIFT")
        require(type(self.state["calls"]) is int and 0 <= self.state["calls"] <= MAX_CALLS
                and type(self.state["intents"]) is dict and len(self.state["intents"]) <= 4, "INVALID_JOURNAL")
        for key, record in self.state["intents"].items():
            exact(record, {"id", "action", "group", "facts", "request", "approval", "phase", "attempts", "observed_status", "observation_sha256"}, "INVALID_INTENT")
            require(key == record["id"] == digest({"workflow": workflow, "action": record["action"], "group": record["group"]}), "INTENT_ID_MISMATCH")
            require(record["phase"] in {"PREPARED", "UNCERTAIN", "OBSERVED"} and type(record["attempts"]) is int
                    and record["attempts"] in (0, 1) and (record["phase"] == "PREPARED") == (record["attempts"] == 0), "INVALID_INTENT")
            validate_request(self.profile, record["request"])
            validate_facts(self.profile, record["facts"])
            require(record["request"] == request_for(self.profile, record["facts"]["user"]["id"], record["action"], record["group"]), "INTENT_TARGET_MISMATCH")
            try: grant = TrustedApproval(**record["approval"])
            except (TypeError, ValueError): raise EntraError("INVALID_INTENT_APPROVAL") from None
            require(grant.workflow == workflow and grant.profile_sha256 == digest(self.profile)
                    and grant.facts_sha256 == digest(record["facts"]) and grant.request_sha256 == digest(record["request"]), "INTENT_APPROVAL_MISMATCH")
            require(record["observed_status"] is None or (type(record["observed_status"]) is int
                    and 100 <= record["observed_status"] <= 599), "INVALID_INTENT")
            require(record["observation_sha256"] is None or (type(record["observation_sha256"]) is str
                    and re.fullmatch(r"[0-9a-f]{64}", record["observation_sha256"])), "INVALID_INTENT")
    def save(self):
        raw = canonical(self.state); require(len(raw) <= 65536, "JOURNAL_TOO_LARGE")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix+".tmp")
        with temporary.open("wb") as stream: stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, self.path)
    def charge(self):
        require(self.state["calls"] < MAX_CALLS, "CALL_BUDGET_EXHAUSTED")
        self.state["calls"] += 1; self.save()

class EntraAdapter:
    def __init__(self, p, journal, attestation, approval_verifier, *, reader=None, token_loader=None,
                 clock=time.monotonic, wall_clock=time.time, deadline=None):
        self._profile = profile(p); self.journal = journal
        require(journal.state["profile_sha256"] == digest(self._profile), "PROFILE_OR_WORKFLOW_DRIFT")
        self.attestation, self.approval_verifier = attestation, approval_verifier
        self.reader = reader if reader is not None else DisabledReader()
        self.token_loader = token_loader  # Opaque trusted interface; never invoked in this slice.
        self.clock, self.wall_clock = clock, wall_clock
        now = clock(); self.deadline = now+30 if deadline is None else deadline
        require(type(self.deadline) in (int, float) and math.isfinite(self.deadline) and now < self.deadline <= now+30, "INVALID_DEADLINE")
        self.events, self._reading = [], False
    def _gate(self):
        a = self.attestation
        require(type(a) is TrustedAttestation and a.profile_sha256 == digest(self._profile)
                and a.tenant_id == self._profile["tenant_id"] and a.app_id == self._profile["app_id"]
                and a.isolated is True and type(a.non_admin_users) is tuple
                and all(type(u) is str for u in a.non_admin_users)
                and set(a.non_admin_users) == set(self._profile["users"].values())
                and type(a.permissions) is tuple and all(type(s) is str for s in a.permissions)
                and PERMISSIONS <= set(a.permissions), "TRUSTED_PREFLIGHT_REQUIRED")
        require(type(a.expires_at) in (int, float) and math.isfinite(a.expires_at) and self.wall_clock() < a.expires_at, "ATTESTATION_EXPIRED")
        require(self.clock() < self.deadline, "TOTAL_DEADLINE")
    def _event(self, code, *, status=None, intent=None):
        value = {"version": VERSION, "mode": "injected-double", "remote_dispatch": False,
                 "profile_sha256": digest(self._profile), "workflow_sha256": digest(self.journal.workflow),
                 "code": code, "status": status, "calls": self.journal.state["calls"], "intent_sha256": intent}
        self.events.append(value)
    def _read(self, url):
        self._gate()
        request = {"method": "GET", "url": url, "body": None}; validate_request(self._profile, request)
        require(getattr(self.reader, "kind", None) == "injected-double", "REMOTE_DISPATCH_DISABLED")
        require(not self._reading, "REQUEST_ALREADY_IN_FLIGHT")
        self.journal.charge(); end = min(self.deadline, self.clock()+5)
        self._reading = True
        try: reply = self.reader.read(copy.deepcopy(request), end)
        except Exception:
            self._event("READ_UNCERTAIN"); raise EntraError("READ_UNCERTAIN") from None
        finally: self._reading = False
        require(self.clock() < end, "LATE_READ")
        require(type(reply) is Reply and type(reply.status) is int and 100 <= reply.status <= 599
                and type(reply.body) is bytes and len(reply.body) <= MAX_REPLY and type(reply.headers) is dict
                and len(reply.headers) <= 16 and all(type(k) is str and type(v) is str and len(k) <= 128
                and len(v) <= 2048 for k, v in reply.headers.items()), "INVALID_REPLY")
        self._event("READ_REPLY", status=reply.status)
        if reply.status != 200: raise EntraError("HTTP_"+str(reply.status))
        require(reply.headers.get("Content-Type", "").split(";")[0].lower() == "application/json", "REPLY_MEDIA_TYPE")
        try: return strict(reply.body)
        except ValueError: raise EntraError("REPLY_JSON") from None
    def intake(self, employee):
        with self.journal.lock:
            self._gate(); require(employee in self._profile["users"], "EMPLOYEE_NOT_ALLOWED")
            org = self._read(ORIGIN+"/organization?$select=id")
            exact(org, {"value"}, "ORGANIZATION_SCHEMA", ("@odata.context",))
            require(type(org["value"]) is list and len(org["value"]) == 1, "TENANT_DRIFT")
            exact(org["value"][0], {"id"}, "ORGANIZATION_SCHEMA")
            require(org["value"][0]["id"] == self._profile["tenant_id"], "TENANT_DRIFT")
            user = self._profile["users"][employee]
            facts = user_facts(self._read(ORIGIN+"/users/"+user+"?$select="+USER_SELECT), user)
            url, seen, members = ORIGIN+"/users/"+user+"/memberOf?$select=id&$top=20", set(), []
            for _ in range(MAX_PAGES):
                require(url not in seen, "PAGINATION_LOOP"); seen.add(url)
                page = self._read(url); exact(page, {"value"}, "MEMBERSHIP_SCHEMA", ("@odata.context", "@odata.nextLink"))
                require(type(page["value"]) is list and len(page["value"]) <= 20, "MEMBERSHIP_SCHEMA")
                for item in page["value"]:
                    exact(item, {"id", "@odata.type"}, "MEMBERSHIP_SCHEMA")
                    require(item["@odata.type"] == "#microsoft.graph.group" and item["id"] in self._profile["groups"], "MEMBER_TYPE_OR_ALLOWLIST")
                    require(item["id"] not in members, "DUPLICATE_MEMBERSHIP"); members.append(item["id"])
                if "@odata.nextLink" not in page: break
                url = page["@odata.nextLink"]; validate_request(self._profile, {"method": "GET", "url": url, "body": None})
                require(urlsplit(url).path == "/v1.0/users/"+user+"/memberOf", "PAGINATION_TARGET_DRIFT")
            else: raise EntraError("PAGE_BUDGET_EXHAUSTED")
            groups = [group_facts(self._read(ORIGIN+"/groups/"+g+"?$select="+GROUP_SELECT), g) for g in self._profile["groups"]]
            self._gate()
            return {"tenant_id": self._profile["tenant_id"], "employee_id": employee, "user": facts, "members": sorted(members), "groups": groups}
    def _approve(self, grant, facts, request):
        self._gate()
        require(type(grant) is TrustedApproval and grant.workflow == self.journal.workflow
                and grant.profile_sha256 == digest(self._profile) and grant.facts_sha256 == digest(facts)
                and grant.request_sha256 == digest(request) and type(grant.proof_ref) is str
                and re.fullmatch(r"[A-Za-z0-9_-]{1,80}", grant.proof_ref), "APPROVAL_BINDING")
        require(type(grant.expires_at) in (int, float) and math.isfinite(grant.expires_at) and self.wall_clock() < grant.expires_at, "APPROVAL_EXPIRED")
        try: trusted = self.approval_verifier(grant)
        except Exception: trusted = False
        require(trusted is True, "AUTHORITY_APPROVAL_REQUIRED")
    def prepare(self, facts, action, grant, group=None):
        with self.journal.lock:
            validate_facts(self._profile, facts)
            request = request_for(self._profile, facts["user"]["id"], action, group); self._approve(grant, facts, request)
            key = digest({"workflow": self.journal.workflow, "action": action, "group": group})
            existing = self.journal.state["intents"].get(key)
            if existing:
                require(existing["facts"] == facts and existing["request"] == request, "DUPLICATE_INTENT_DRIFT")
                return copy.deepcopy(existing)
            require(len(self.journal.state["intents"]) < 4, "INTENT_BUDGET_EXHAUSTED")
            fresh = self.intake(facts["employee_id"]); require(fresh == facts, "APPROVAL_FACT_DRIFT")
            require(action != "disable" or fresh["user"]["accountEnabled"] is True, "NO_DISABLE_TRANSITION")
            require(action != "remove_membership" or group in fresh["members"], "NO_MEMBERSHIP_TRANSITION")
            self._approve(grant, fresh, request)
            record = {"id": key, "action": action, "group": group, "facts": fresh, "request": request,
                      "approval": asdict(grant), "phase": "PREPARED", "attempts": 0,
                      "observed_status": None, "observation_sha256": None}
            self.journal.state["intents"][key] = record; self.journal.save(); self._event("INTENT_PREPARED", intent=key)
            return copy.deepcopy(record)
    def dispatch(self, intent_id):
        """Unconditional gate, before transport or token-loader access."""
        raise EntraError("REMOTE_DISPATCH_DISABLED")
    def _record(self, intent_id):
        require(type(intent_id) is str and re.fullmatch(r"[0-9a-f]{64}", intent_id)
                and intent_id in self.journal.state["intents"], "UNKNOWN_INTENT")
        return self.journal.state["intents"][intent_id]
    def reserve_contract_attempt(self, intent_id, grant):
        """Trusted simulated crash boundary ONLY; does not send a mutation."""
        with self.journal.lock:
            record = self._record(intent_id)
            self._approve(grant, record["facts"], record["request"])
            require(record["attempts"] == 0, "ATTEMPT_ALREADY_RESERVED")
            require(self.intake(record["facts"]["employee_id"]) == record["facts"], "APPROVAL_FACT_DRIFT")
            self._approve(grant, record["facts"], record["request"])
            record["attempts"] = 1; record["phase"] = "UNCERTAIN"; self.journal.save()
            self._event("SIMULATED_ATTEMPT_RESERVED", intent=intent_id)
    def observe_contract_reply(self, intent_id, status):
        """Status from trusted simulation; even a 2xx does not establish completion."""
        with self.journal.lock:
            record = self._record(intent_id)
            require(record["attempts"] == 1 and type(status) is int and 100 <= status <= 599, "INVALID_ATTEMPT_OBSERVATION")
            record["observed_status"] = status; self.journal.save(); self._event("SIMULATED_REPLY", status=status, intent=intent_id)
    def reconcile(self, intent_id):
        with self.journal.lock:
            record = self._record(intent_id); require(record["attempts"] == 1, "NO_ATTEMPT_TO_RECONCILE")
            before = record["facts"]
            try:
                after = self.intake(before["employee_id"])
                stable = after["tenant_id"] == before["tenant_id"] and after["groups"] == before["groups"]
                stable &= all(after["user"][k] == before["user"][k] for k in ("id", "userType", "onPremisesSyncEnabled"))
                action, observed = record["action"], False
                if action == "disable":
                    observed = stable and before["user"]["accountEnabled"] is True and after["user"]["accountEnabled"] is False \
                        and after["members"] == before["members"] and after["user"]["signInSessionsValidFromDateTime"] == before["user"]["signInSessionsValidFromDateTime"]
                elif action == "revoke":
                    observed = stable and after["members"] == before["members"] and after["user"]["accountEnabled"] == before["user"]["accountEnabled"] \
                        and stamp(after["user"]["signInSessionsValidFromDateTime"]) > stamp(before["user"]["signInSessionsValidFromDateTime"])
                else:
                    observed = stable and after["user"] == before["user"] \
                        and set(after["members"]) == set(before["members"])-{record["group"]}
                record["observation_sha256"] = digest(after)
            except EntraError:
                observed = False; record["observation_sha256"] = None
            record["phase"] = "OBSERVED" if observed else "UNCERTAIN"; self.journal.save()
            self._event("POSTCONDITION_OBSERVED" if observed else "READBACK_INCONCLUSIVE", intent=intent_id)
            return {"phase": record["phase"], "postcondition_observed": bool(observed),
                    "mutation_attribution": "unknown", "all_sessions_stopped": False,
                    "automatic_mutation_retries": 0, "observation_sha256": record["observation_sha256"]}
