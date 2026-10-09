"""Independent outcome/audit verifier. It never calls Java or reads actor prose."""
from datetime import datetime
import hashlib
from pathlib import Path
import re
import struct
import xml.etree.ElementTree as ET

STEPS = ("disable_login", "revoke_sessions", "remove_grants", "create_collection_task", "complete_hr")
JOIN = ("prepare_account", "add_role_grants", "reserve_asset", "enable_login", "complete_onboarding_hr")
CLEANUP = ("compensate_account", "undo_role_grants", "release_asset", "fail_onboarding_hr")
BUNDLES = {"engineer": {"employees", "engineering"}, "support": {"employees", "support"}}


def snapshot_files(run_dir, service):
    return sorted(p for p in (Path(run_dir) / service).glob("*.xml") if re.fullmatch(r"[0-9]{20}\.xml", p.name))


def parse_snapshot(path):
    raw = Path(path).read_bytes()
    if len(raw) > 4 * 1024 * 1024 or b"<!" in raw:
        raise AssertionError("unsafe/corrupt snapshot")
    root = ET.fromstring(raw)
    if root.tag != "snapshot" or root.attrib != {"schema": "1"}:
        raise AssertionError("unknown committed snapshot schema")
    fields = {}
    for child in root:
        if child.tag != "field" or len(child) or set(child.attrib) != {"name"}:
            raise AssertionError("invalid snapshot topology")
        key = child.attrib["name"]
        if key in fields:
            raise AssertionError("duplicate snapshot field")
        fields[key] = child.text or ""
    return fields


def read_snapshot(run_dir, service):
    files = snapshot_files(run_dir, service)
    if not files:
        raise AssertionError(f"missing committed {service} snapshot")
    return parse_snapshot(files[-1])


def field_digest(fields):
    data = bytearray()
    for key, value in sorted(fields.items()):
        for text in (key, value):
            encoded = text.encode("utf-8")
            data.extend(struct.pack(">I", len(encoded)))
            data.extend(encoded)
    return hashlib.sha256(data).hexdigest()


def plan_digest(w):
    intent = w["intent"]
    fields = {k: w[k] for k in ("workflow_id", "employee_id", "intent", "role", "epoch")}
    fields.update(policy_id="onboarding-v1" if intent == "onboard" else "offboarding-v1",
                  policy_version="1", steps=",".join(JOIN if intent == "onboard" else STEPS),
                  compensation=",".join(CLEANUP) + ":owned_only" if intent == "onboard"
                  else "disable_login,revoke_sessions,remove_grants:never_restore_access")
    fields.update({k: v for k, v in w.items() if k.startswith("approved.")})
    return field_digest(fields)


def grants(record):
    return set(filter(None, record["grants"].split(",")))


def verify_run(run_dir, expected):
    records = {n: read_snapshot(run_dir, n) for n in ("workflow", "hr", "identity", "assets")}
    w, hr, identity, assets = (records[n] for n in ("workflow", "hr", "identity", "assets"))
    assertions = []

    def check(condition, label):
        if not condition:
            raise AssertionError(label)
        assertions.append(label)

    check(all(s["employee_id"] == expected["employee_id"] for s in records.values()), "employee identity agrees across stores")
    check(w["administrative_status"] == expected["administrative_status"], "expected administrative disposition")
    check(identity["enabled"] == str(expected["enabled"]).lower(), "expected login state")
    check(int(identity["sessions"]) == expected["sessions"], "expected modeled session count")
    check(grants(identity) == set(expected["grants"]), "exact managed grants")
    check(hr["administrative_status"] == expected["hr_status"], "expected HR state")
    check(assets["collection_status"] == expected["collection_status"], "collection task status; no physical return claim")
    check(bool(assets["collection_task"]) == expected["collection_task"], "expected collection task presence")
    for key in ("account_exists", "account_state"):
        if key in expected:
            check(identity[key] == str(expected[key]).lower() if type(expected[key]) is bool else identity[key] == expected[key], "expected " + key)
    for key in ("asset_id", "inventory_available"):
        if key in expected:
            value = str(expected[key]).lower() if type(expected[key]) is bool else expected[key]
            check(assets[key] == value, "expected " + key)
    if expected.get("event_sequence") is not None:
        check(hr["event_sequence"] == str(expected["event_sequence"]), "authoritative event sequence")
    if "reason" in expected:
        check(w["reason"] == expected["reason"], "expected unresolved/cancellation reason")
    if assets["collection_task"] and "asset_id" in assets:
        check(assets["collection_task"] == f"collect-{identity['employee_id']}-{assets['asset_id']}", "exact single collection task ID")
    effect_total = 0
    for name in ("hr", "identity", "assets"):
        record = records[name]
        prefix = "effect." if any(k.startswith("effect.") for k in record) else "effects."
        for key, value in record.items():
            if key.startswith(prefix):
                check(int(value) in (0, 1), f"{name}/{key} has no duplicate business effect")
                effect_total += int(value)
                if prefix == "effect.":
                    check(key.replace("effect.", "ledger.", 1) in record, "effect has committed service receipt")
                    check(key.replace("effect.", "audit.", 1) in record, "effect has audit receipt")
        # Aliases are diagnostic, but must not conceal a duplicate or a removed receipt.
        for key, value in record.items():
            if key.startswith("effects."):
                check(int(value) in (0, 1), f"{name}/{key} has no duplicate business effect")
                check("receipt." + key[8:] in record, "effect alias has committed receipt")
    check(effect_total == expected["business_effects"], "exact business effect count")
    intent = w.get("intent", "offboard")
    steps = JOIN if intent == "onboard" else STEPS
    if expected["administrative_status"] == "AWAITING_APPROVAL":
        check(all(records[n]["version"] == parse_snapshot(snapshot_files(run_dir, n)[0])["version"] for n in ("hr", "identity", "assets")), "unapproved case has zero service commits")
        check(all(w["step." + a] == "PENDING" for a in steps), "unapproved case has zero executed steps")
    if expected["administrative_status"] == "BLOCKED" and intent == "offboard":
        unresolved = expected.get("blocked_step", "create_collection_task")
        check(w["step." + unresolved] == "PENDING", "required step remains unresolved")
        check(w["attempts." + unresolved] == "3", "service retries bounded to three")
        check(w["step.complete_hr"] == "PENDING", "blocked administrative process cannot complete HR")
    if expected["administrative_status"] == "COMPLETED":
        check(all(w["step." + a] == "DONE" for a in steps), "all five required steps verified")
        check(hr["administrative_status"] == ("ONBOARDED" if intent == "onboard" else "OFFBOARDED"), "completion agrees with HR")
        for a in steps:
            service = "identity" if a in STEPS[:3] + JOIN[:2] + ("enable_login",) else "assets" if a in {"create_collection_task", "reserve_asset"} else "hr"
            check("receipt." + a in records[service], f"{a} has a committed service receipt")
    if expected.get("recovered_step"):
        check(w.get("recovered_receipt") == expected["recovered_step"], "lost acknowledgement recovered from service receipt")
    if "provider_turns" in w:
        check(0 <= int(w["provider_turns"]) <= int(w["turn_limit"]) <= 24, "persisted provider turn budget")
        check(0 <= int(w["actor_calls"]) <= 32, "persisted actor tool budget")
        check(0 <= int(w["active_reserved_ms"]) <= 120000, "persisted active time reservation")
        check(0 <= int(w["safety_calls"]) <= 12, "separate safety budget")
        for key, value in w.items():
            if key.startswith("attempts."):
                check(0 <= int(value) <= 3, "bounded attempts " + key)
        audit_history(run_dir, records, expected, check)
    if expected.get("preserve_existing"):
        original = parse_snapshot(snapshot_files(run_dir, "identity")[0])
        check(identity["account_exists"] == original["account_exists"], "pre-existing account preserved")
        check(grants(identity) == grants(original), "pre-existing grants preserved exactly")
        check(identity["account_state"] == original["account_state"], "pre-existing account state preserved")
    return {"passed": True, "assertion_count": len(assertions), "assertions": assertions,
            "business_effects": effect_total, "provider_quality_evaluated": False}


def audit_history(run_dir, records, expected, check):
    histories = {n: [parse_snapshot(p) for p in snapshot_files(run_dir, n)] for n in records}
    approved = {}
    for w in histories["workflow"]:
        if "approval_digest" in w:
            check(w["approval_digest"] == w["digest"] == plan_digest(w), "approved plan digest independently matches fields")
            approved[w["workflow_id"]] = w
    for name in ("hr", "identity", "assets"):
        previous = histories[name][0]
        for current in histories[name][1:]:
            check(all(current.get(k) == v for k, v in previous.items() if k.startswith(("ledger.", "audit.", "effect."))), "immutable receipts and effect audit preserved")
            new = [k for k in current if k.startswith("ledger.") and k not in previous]
            check(len(new) <= 1, "one service operation per commit")
            if not new:
                if name == "identity" and (grants(previous) != grants(current) or previous["enabled"] != current["enabled"]):
                    check(expected.get("allow_external_edit", False) and current.get("external_edit") == "authored-fixture", "unreceipted identity edit forbidden")
                previous = current
                continue
            key = new[0]
            _, seq, action = key.split(".", 2)
            receipt = current[key]
            operation, payload = receipt.rsplit(":", 1)
            workflow, epoch, actual_action = operation.split("/")
            check(action == actual_action and workflow in approved, "service receipt refers to approved workflow")
            plan = approved[workflow]
            check(payload == field_digest({"digest": plan["digest"], "step": action}), "receipt payload matches exact approved action")
            check(epoch == plan["epoch"], "operation epoch matches approval")
            check(current.get("receipt." + action) == receipt, "service alias agrees with immutable receipt")
            audit = current[key.replace("ledger.", "audit.", 1)].split("|")
            check(len(audit) == 6, "complete independent audit context")
            order, source_seq, source_epoch, source_intent, instant, mode = audit
            check(int(current["commit_order"]) == int(order) > int(previous["commit_order"]), "service commit ordering")
            authority = max((h for h in histories["hr"] if int(h["commit_order"]) <= int(order)), key=lambda h: int(h["commit_order"]))
            check((source_seq, source_epoch, source_intent) == (authority["event_sequence"], authority["epoch"], authority["intent"]), "receipt matches authoritative event at commit")
            check(int(current["version"]) == int(previous["version"]) + 1, "one version per receipted commit")
            if mode == "forward":
                check(action in (JOIN if plan["intent"] == "onboard" else STEPS), "action allowed by finite policy")
                check((seq, epoch, plan["intent"]) == (source_seq, source_epoch, source_intent), "superseded forward action forbidden")
                check(authority["role"] == plan["role"] and authority["event_id"] == plan["approved.event_id"]
                      and authority["effective_at"] == plan["approved.effective_at"], "forward approval matches authoritative role and event payload")
                when = datetime.fromisoformat(instant)
                check(datetime.fromisoformat(plan["approved.effective_at"]) <= when < datetime.fromisoformat(plan["approval_expires"]), "forward mutation effective and unexpired")
            else:
                check(mode == "safety" and action in (CLEANUP if plan["intent"] == "onboard" else STEPS[:3]), "safety action approved and finite")
                if action == "fail_onboarding_hr":
                    check(seq == source_seq and epoch == source_epoch, "cleanup cannot overwrite successor HR event")
            if name == "identity":
                added = grants(current) - grants(previous)
                enabled = previous["enabled"] == "false" and current["enabled"] == "true"
                if added or enabled:
                    check(mode == "forward" and plan["intent"] == "onboard", "access additions require forward onboarding approval")
                    check(added <= BUNDLES[plan["role"]] and grants(current) <= BUNDLES[plan["role"]], "no forbidden grant at any committed generation")
                    check(not enabled or action == "enable_login", "enablement only in approved late step")
                if added:
                    check(action == "add_role_grants" and current.get("grants_added_by") == workflow, "added grant ownership matches approved workflow")
                    check(set(filter(None, current.get("added_grants", "").split(","))) == added, "owned grant set matches exact additions")
                if enabled:
                    prior_assets = max((a for a in histories["assets"] if int(a["commit_order"]) < int(order)), key=lambda a: int(a["commit_order"]))
                    check(prior_assets["asset_id"] == plan["approved.inventory_id"] and prior_assets.get("reserved_by") == workflow, "enablement requires prior owned asset reservation")
                    check(grants(current) == BUNDLES[plan["role"]] and current.get("enabled_by") == workflow, "enabled role and owner match approval")
                if action == "undo_role_grants":
                    check(grants(previous) - grants(current) <= set(filter(None, previous.get("added_grants", "").split(","))), "cleanup removes only workflow-owned grants")
                    if grants(previous) != grants(current):
                        check(previous.get("grants_added_by") == workflow, "cleanup grant owner matches workflow")
                if action == "compensate_account":
                    if previous["enabled"] == "true" and current["enabled"] == "false":
                        check(previous.get("enabled_by") == workflow, "cleanup disablement has workflow ownership")
                    if previous.get("account_state") != "TOMBSTONE" and current.get("account_state") == "TOMBSTONE":
                        check(previous.get("created_by") == workflow, "only workflow-created account is tombstoned")
            if name == "assets" and action == "release_asset" and current["asset_id"] != previous["asset_id"]:
                check(previous.get("reserved_by") == workflow and not current["asset_id"], "cleanup releases only owned asset")
            previous = current

