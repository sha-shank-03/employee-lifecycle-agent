"""Authored fictional injected-contract fixtures, not a tenant/account or scored dataset."""
import copy
from urllib.parse import urlsplit
from agent.entra_contract import PERMISSIONS, VERSION, Reply, TrustedApproval, TrustedAttestation
from agent.gateway import canonical, digest

TENANT, APP, USER, G1, G2 = [c*8+"-"+c*4+"-4"+c*3+"-8"+c*3+"-"+c*12 for c in "12345"]
PROFILE = {"schema": 1, "version": VERSION, "mode": "injected-double", "tenant_id": TENANT,
           "app_id": APP, "users": {"E-104": USER}, "groups": [G1, G2], "remote_dispatch": False}

def response(value, status=200, headers=None):
    return Reply(status, canonical(value), {"Content-Type": "application/json"} if headers is None else headers)

class FakeGraph:
    kind = "injected-double"
    def __init__(self):
        self.requests, self.override = [], None
        self.user = {"id": USER, "accountEnabled": True, "userType": "Member", "onPremisesSyncEnabled": None,
                     "signInSessionsValidFromDateTime": "2026-10-01T00:00:00Z"}
        self.groups = {g: {"id": g, "groupTypes": [], "securityEnabled": True, "mailEnabled": False,
                      "isAssignableToRole": False, "membershipRule": None, "onPremisesSyncEnabled": None} for g in (G1, G2)}
        self.members = [G1, G2]
    def read(self, request, deadline):
        self.requests.append(copy.deepcopy(request))
        if self.override:
            value = self.override(request)
            if value is not None: return value
        path = urlsplit(request["url"]).path
        if path == "/v1.0/organization": return response({"value": [{"id": TENANT}]})
        if path == "/v1.0/users/"+USER: return response(self.user)
        if path == "/v1.0/users/"+USER+"/memberOf":
            return response({"value": [{"id": g, "@odata.type": "#microsoft.graph.group"} for g in self.members]})
        if path.startswith("/v1.0/groups/"): return response(self.groups[path.rsplit("/", 1)[1]])
        raise AssertionError("Unexpected fictional read route")

def attestation(p=PROFILE):
    return TrustedAttestation(digest(p), p["tenant_id"], p["app_id"], tuple(p["users"].values()),
                              True, tuple(sorted(PERMISSIONS)), 2000)

def approval(facts, request, workflow="wf-fictional", p=PROFILE):
    return TrustedApproval(workflow, digest(p), digest(facts), digest(request), 2000, "fictional-java-proof")

def authority(grant):
    return grant.proof_ref == "fictional-java-proof"
