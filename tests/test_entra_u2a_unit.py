"""PURE U2-A injected contracts; Popen/socket.socket prohibited. No bearer token loaded."""
import copy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from agent.bridge import ROOT
from agent.entra_contract import EntraAdapter, EntraError, IntentJournal, ORIGIN, Reply, profile, request_for, validate_request
from agent.gateway import canonical, digest
from tests.entra_fixtures import APP, G1, G2, PROFILE, TENANT, USER, FakeGraph, approval, attestation, authority, response

class EntraPure(unittest.TestCase):
    def setUp(self):
        for target in ("subprocess.Popen", "socket.socket"):
            guard = patch(target, side_effect=AssertionError("pure contract attempted native operation"))
            guard.start(); self.addCleanup(guard.stop)
        (ROOT/"work").mkdir(exist_ok=True)
        folder = tempfile.TemporaryDirectory(prefix="u2a-pure-", dir=ROOT/"work"); self.addCleanup(folder.cleanup)
        self.path, self.now = Path(folder.name)/"intents.json", [0.0]
        self.graph = FakeGraph(); self.journal = IntentJournal(self.path, PROFILE, "wf-fictional")
        self.adapter = self.make()
    def make(self, **kwargs):
        return EntraAdapter(PROFILE, self.journal, attestation(), authority, reader=self.graph,
                            clock=lambda: self.now[0], wall_clock=lambda: 1000, **kwargs)
    def plan(self, action="revoke", group=None):
        facts = self.adapter.intake("E-104"); request = request_for(PROFILE, USER, action, group)
        grant = approval(facts, request); record = self.adapter.prepare(facts, action, grant, group)
        return record, grant
    def reserved(self, action="revoke", group=None):
        record, grant = self.plan(action, group); self.adapter.reserve_contract_attempt(record["id"], grant)
        return record, grant
    def test_intake_selects_fixed_read_routes(self):
        facts = self.adapter.intake("E-104")
        self.assertEqual(facts["members"], [G1, G2]); self.assertEqual(len(self.graph.requests), 5)
        self.assertTrue(all(r["method"] == "GET" and set(r) == {"method", "url", "body"} for r in self.graph.requests))
    def test_default_reader_and_remote_profile_are_disabled(self):
        disabled = EntraAdapter(PROFILE, self.journal, attestation(), authority, wall_clock=lambda: 1000)
        with self.assertRaisesRegex(EntraError, "REMOTE_DISPATCH_DISABLED"): disabled.intake("E-104")
        for field, value in (("remote_dispatch", True), ("mode", "live"), ("tenant_id", "other"), ("schema", True)):
            with self.subTest(field=field), self.assertRaises(EntraError): profile({**PROFILE, field: value})
    def test_token_loader_is_never_invoked(self):
        class Loader:
            def load(self, *args): raise AssertionError("Token loader was invoked")
        adapter = self.make(token_loader=Loader()); adapter.intake("E-104")
        with self.assertRaisesRegex(EntraError, "REMOTE_DISPATCH_DISABLED"): adapter.dispatch("untrusted")
    def test_noncanonical_ids_alias_users_and_unknown_profile_fields(self):
        changes = [{"extra": "raw"}, {"users": {"E-104": USER, "E-105": USER}}, {"groups": [G2, G1]}, {"app_id": APP.upper()}]
        # This fixture's GUID is numeric; explicitly malformed punctuation still rejects.
        changes[-1] = {"app_id": APP+"/path"}
        for change in changes:
            with self.subTest(change=change), self.assertRaises(EntraError): profile({**PROFILE, **change})
    def test_attestation_tenant_app_profile_admin_and_permissions_drift(self):
        a = attestation()
        for change in ({"tenant_id": APP}, {"app_id": TENANT}, {"profile_sha256": "0"*64}, {"isolated": False},
                       {"non_admin_users": ()}, {"permissions": ()}, {"expires_at": 999}):
            self.adapter.attestation = replace(a, **change)
            with self.subTest(change=change), self.assertRaises(EntraError): self.adapter.intake("E-104")
        self.assertFalse(self.graph.requests)
    def test_decoded_claims_are_not_an_attestation(self):
        self.adapter.attestation = {"tid": TENANT, "appid": APP, "roles": ["User.Read.All"]}
        with self.assertRaisesRegex(EntraError, "TRUSTED_PREFLIGHT_REQUIRED"): self.adapter.intake("E-104")
    def test_organization_cross_tenant_or_missing_schema(self):
        for value in ({"value": [{"id": APP}]}, {"value": []}, {"value": [{"name": "untrusted"}]}, {"value": [{"id": TENANT}, {"id": APP}]}):
            self.graph.override = lambda _, v=value: response(v)
            with self.subTest(value=value), self.assertRaises(EntraError): self.adapter.intake("E-104")
    def test_user_object_types_fields_and_cloud_profile(self):
        original = copy.deepcopy(self.graph.user)
        for change in ({"id": APP}, {"userType": "Guest"}, {"accountEnabled": 1}, {"onPremisesSyncEnabled": True},
                       {"signInSessionsValidFromDateTime": None}, {"@odata.type": "#microsoft.graph.agentUser"}, {"extra": "raw"}):
            self.graph.user = {**original, **change}
            with self.subTest(change=change), self.assertRaises(EntraError): self.adapter.intake("E-104")
        self.graph.user = {k: v for k, v in original.items() if k != "accountEnabled"}
        with self.assertRaises(EntraError): self.adapter.intake("E-104")
    def test_role_dynamic_mail_synced_or_missing_group_fields(self):
        original = copy.deepcopy(self.graph.groups[G1])
        for change in ({"id": APP}, {"groupTypes": ["DynamicMembership"]}, {"isAssignableToRole": True},
                       {"isAssignableToRole": None}, {"mailEnabled": True}, {"securityEnabled": 1},
                       {"onPremisesSyncEnabled": True}, {"membershipRule": "rule"}, {"@odata.type": "#microsoft.graph.user"}):
            self.graph.groups[G1] = {**original, **change}
            with self.subTest(change=change), self.assertRaises(EntraError): self.adapter.intake("E-104")
        self.graph.groups[G1] = {k: v for k, v in original.items() if k != "isAssignableToRole"}
        with self.assertRaises(EntraError): self.adapter.intake("E-104")
    def test_wrong_membership_object_type_or_group(self):
        for item in ({"id": G1, "@odata.type": "#microsoft.graph.directoryRole"},
                     {"id": APP, "@odata.type": "#microsoft.graph.group"}, {"id": G1}):
            self.graph.override = lambda r, i=item: response({"value": [i]}) if "/memberOf?" in r["url"] else None
            with self.subTest(item=item), self.assertRaises(EntraError): self.adapter.intake("E-104")
    def test_pagination_collects_all_before_absence_claim(self):
        def pages(r):
            if "/memberOf?" not in r["url"]: return None
            if "$skiptoken=" in r["url"]: return response({"value": [{"id": G2, "@odata.type": "#microsoft.graph.group"}]})
            return response({"value": [{"id": G1, "@odata.type": "#microsoft.graph.group"}],
                             "@odata.nextLink": ORIGIN+"/users/"+USER+"/memberOf?$select=id&$top=20&$skiptoken=opaque"})
        self.graph.override = pages; self.assertEqual(self.adapter.intake("E-104")["members"], [G1, G2])
    def test_cross_host_path_user_query_and_credentials_nextlink_denied(self):
        base = ORIGIN+"/users/"+USER+"/memberOf?$select=id&$top=20"
        links = [base.replace("graph.microsoft.com", "elsewhere.invalid"), base.replace(USER, APP),
                 base.replace("/v1.0/", "/beta/"), base+"&$filter=raw", base+"#fragment",
                 base.replace("graph.microsoft.com", "user:password@graph.microsoft.com"),
                 base.replace("graph.microsoft.com", "graph.microsoft.com:443")]
        for link in links:
            self.graph.override = lambda r, link=link: response({"value": [], "@odata.nextLink": link}) if "/memberOf?" in r["url"] else None
            with self.subTest(link=link), self.assertRaises(EntraError): self.adapter.intake("E-104")
    def test_repeated_pages_duplicate_members_and_page_cap(self):
        base = ORIGIN+"/users/"+USER+"/memberOf?$select=id&$top=20"
        self.graph.override = lambda r: response({"value": [], "@odata.nextLink": base}) if "/memberOf?" in r["url"] else None
        with self.assertRaisesRegex(EntraError, "PAGINATION_LOOP"): self.adapter.intake("E-104")
        self.graph.override = lambda r: response({"value": [{"id": G1, "@odata.type": "#microsoft.graph.group"}]*2}) if "/memberOf?" in r["url"] else None
        with self.assertRaisesRegex(EntraError, "DUPLICATE"): self.adapter.intake("E-104")
        count = [0]
        def pages(r):
            if "/memberOf?" in r["url"]:
                count[0] += 1; return response({"value": [], "@odata.nextLink": base+"&$skiptoken="+str(count[0])})
        self.graph.override = pages
        with self.assertRaisesRegex(EntraError, "PAGE_BUDGET"): self.adapter.intake("E-104")
    def test_http_denials_throttling_and_server_failures_do_not_retry(self):
        for status in (401, 403, 404, 429, 500, 503):
            count = len(self.graph.requests); self.graph.override = lambda _, s=status: response({"error": "PRIVATE_SENTINEL"}, s, {"Retry-After": "5"})
            with self.subTest(status=status), self.assertRaisesRegex(EntraError, "HTTP_"+str(status)): self.adapter.intake("E-104")
            self.assertEqual(len(self.graph.requests), count+1)
        self.assertNotIn("PRIVATE_SENTINEL", repr(self.adapter.events))
    def test_malformed_duplicate_nonfinite_media_and_oversize_reply(self):
        for raw, headers in ((b'{"value":NaN}', {"Content-Type": "application/json"}), (b'{"value":[],"value":[]}', {"Content-Type": "application/json"}),
                             (b"{}", {"Content-Type": "text/html"}), (b" "*65537, {"Content-Type": "application/json"}),
                             (b"{}", {"Content-Type": 4})):
            self.graph.override = lambda _, b=raw, h=headers: Reply(200, b, h)
            with self.subTest(raw=raw[:16]), self.assertRaises(EntraError): self.adapter.intake("E-104")
    def test_call_budget_is_persisted_across_restart(self):
        self.journal.state["calls"] = 40; self.journal.save()
        self.journal = IntentJournal(self.path, PROFILE, "wf-fictional"); self.adapter = self.make()
        with self.assertRaisesRegex(EntraError, "CALL_BUDGET"): self.adapter.intake("E-104")
        self.assertFalse(self.graph.requests)
    def test_total_deadline_and_late_reply_are_rejected(self):
        self.now[0] = 31
        with self.assertRaisesRegex(EntraError, "TOTAL_DEADLINE"): self.adapter.intake("E-104")
        self.now[0] = 0
        self.graph.override = lambda _: (self.now.__setitem__(0, 6) or response({"value": [{"id": TENANT}]}))
        with self.assertRaisesRegex(EntraError, "LATE_READ"): self.adapter.intake("E-104")
    def test_absent_untrusted_and_stale_approval(self):
        facts = self.adapter.intake("E-104"); req = request_for(PROFILE, USER, "disable"); grant = approval(facts, req)
        for value in (None, replace(grant, expires_at=999), replace(grant, proof_ref="untrusted"),
                      replace(grant, workflow="other"), replace(grant, profile_sha256="0"*64),
                      replace(grant, facts_sha256="0"*64), replace(grant, request_sha256="0"*64)):
            with self.subTest(value=value), self.assertRaises(EntraError): self.adapter.prepare(facts, "disable", value)
        self.assertFalse(self.journal.state["intents"])
    def test_approved_facts_are_reread_before_intent_and_attempt(self):
        facts = self.adapter.intake("E-104"); req = request_for(PROFILE, USER, "disable")
        self.graph.user["accountEnabled"] = False
        with self.assertRaisesRegex(EntraError, "FACT_DRIFT"): self.adapter.prepare(facts, "disable", approval(facts, req))
        self.graph.user["accountEnabled"] = True; record, grant = self.plan("disable")
        self.graph.members.remove(G1)
        with self.assertRaisesRegex(EntraError, "FACT_DRIFT"): self.adapter.reserve_contract_attempt(record["id"], grant)
        self.assertEqual(self.journal.state["intents"][record["id"]]["attempts"], 0)
    def test_only_three_exact_mutation_shapes_and_mandatory_ref(self):
        valid = request_for(PROFILE, USER, "remove_membership", G1); validate_request(PROFILE, valid)
        invalid = [{**valid, "url": valid["url"].removesuffix("/$ref")}, {**valid, "body": {}},
                   {**valid, "url": valid["url"].replace(G1, APP)}, {**valid, "method": "POST"},
                   {**request_for(PROFILE, USER, "disable"), "body": {"accountEnabled": 0}}]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(EntraError): validate_request(PROFILE, value)
    def test_prepared_intents_never_dispatch_mutations(self):
        facts = self.adapter.intake("E-104")
        for action, group in (("disable", None), ("revoke", None), ("remove_membership", G1), ("remove_membership", G2)):
            req = request_for(PROFILE, USER, action, group); record = self.adapter.prepare(facts, action, approval(facts, req), group)
            self.assertEqual(record["attempts"], 0)
            with self.assertRaisesRegex(EntraError, "REMOTE_DISPATCH_DISABLED"): self.adapter.dispatch(record["id"])
        self.assertEqual(len(self.journal.state["intents"]), 4)
        self.assertTrue(all(r["method"] == "GET" for r in self.graph.requests))
    def test_duplicate_restart_intents_and_attempts_are_not_resent(self):
        record, grant = self.reserved(); before = len(self.graph.requests)
        self.journal = IntentJournal(self.path, PROFILE, "wf-fictional"); self.adapter = self.make()
        self.assertEqual(self.adapter.prepare(record["facts"], "revoke", grant)["attempts"], 1)
        self.assertEqual(len(self.graph.requests), before)
        with self.assertRaisesRegex(EntraError, "ALREADY_RESERVED"): self.adapter.reserve_contract_attempt(record["id"], grant)
    def test_changed_duplicate_intent_is_rejected(self):
        record, _ = self.plan(); facts = copy.deepcopy(record["facts"]); facts["user"]["accountEnabled"] = False
        with self.assertRaisesRegex(EntraError, "DUPLICATE_INTENT_DRIFT"):
            self.adapter.prepare(facts, "revoke", approval(facts, record["request"]))
    def test_2xx_reply_is_not_completion_without_readback(self):
        record, _ = self.reserved(); self.adapter.observe_contract_reply(record["id"], 200)
        self.assertEqual(self.adapter.reconcile(record["id"])["phase"], "UNCERTAIN")
    def test_disable_readback_is_observed_with_unknown_attribution(self):
        record, _ = self.reserved("disable"); self.graph.user["accountEnabled"] = False
        result = self.adapter.reconcile(record["id"])
        self.assertTrue(result["postcondition_observed"]); self.assertEqual(result["mutation_attribution"], "unknown")
        self.assertFalse(result["all_sessions_stopped"])
    def test_lost_revoke_reply_cutoff_readback_and_no_post_retry(self):
        record, grant = self.reserved(); self.assertFalse(self.adapter.reconcile(record["id"])["postcondition_observed"])
        self.graph.user["signInSessionsValidFromDateTime"] = "2026-10-12T07:00:00Z"
        self.assertTrue(self.adapter.reconcile(record["id"])["postcondition_observed"])
        with self.assertRaisesRegex(EntraError, "ALREADY_RESERVED"): self.adapter.reserve_contract_attempt(record["id"], grant)
        self.assertTrue(all(r["method"] == "GET" for r in self.graph.requests))
    def test_membership_absence_requires_existing_user_group_and_full_read(self):
        record, _ = self.reserved("remove_membership", G1); self.graph.members.remove(G1)
        self.assertTrue(self.adapter.reconcile(record["id"])["postcondition_observed"])
        self.graph.override = lambda r: response({}, 404) if "/users/"+USER+"?" in r["url"] else None
        self.assertFalse(self.adapter.reconcile(record["id"])["postcondition_observed"])
    def test_unrelated_readback_drift_stays_inconclusive(self):
        record, _ = self.reserved("revoke"); self.graph.user["accountEnabled"] = False
        self.graph.user["signInSessionsValidFromDateTime"] = "2026-10-12T07:00:00Z"
        self.assertEqual(self.adapter.reconcile(record["id"])["phase"], "UNCERTAIN")
    def test_persisted_profile_workflow_and_record_tamper_are_rejected(self):
        record, _ = self.plan("remove_membership", G1)
        with self.assertRaises(EntraError): IntentJournal(self.path, {**PROFILE, "app_id": TENANT}, "wf-fictional")
        value = json.loads(self.path.read_text()); value["intents"][record["id"]]["request"]["url"] = value["intents"][record["id"]]["request"]["url"].removesuffix("/$ref")
        self.path.write_bytes(canonical(value))
        with self.assertRaises(EntraError): IntentJournal(self.path, PROFILE, "wf-fictional")
    def test_inflight_reentry_is_blocked(self):
        def probe(_):
            with self.assertRaisesRegex(EntraError, "REQUEST_ALREADY_IN_FLIGHT"): self.adapter.intake("E-104")
        self.graph.override = probe; self.adapter.intake("E-104")
        self.assertEqual(len(self.graph.requests), 5)
    def test_transport_exception_and_events_are_redacted(self):
        def lost(_): raise OSError("PRIVATE_AUTHORIZATION_AND_BODY")
        self.graph.override = lost
        with self.assertRaisesRegex(EntraError, "^READ_UNCERTAIN$"): self.adapter.intake("E-104")
        text = json.dumps(self.adapter.events)
        for value in ("PRIVATE_AUTHORIZATION_AND_BODY", USER, TENANT, APP, "https://", "Authorization"):
            self.assertNotIn(value, text)

if __name__ == "__main__": unittest.main()
