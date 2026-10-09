"""Finite v1 tool protocol; this module contains no domain mutation authority."""
from dataclasses import dataclass
import json
import struct
import xml.etree.ElementTree as ET

MAX_FRAME = 65_536
TOOLS = {
    "inspect_employee": {"employee_id"},
    "read_policy": {"policy_id"},
    "propose_plan": {"employee_id", "intent"},
    "workflow_status": {"workflow_id"},
    "execute_step": {"workflow_id", "step_id"},
    "verify_outcome": {"workflow_id"},
    "request_handoff": {"workflow_id", "reason_code"},
}


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, str]


@dataclass(frozen=True)
class FinalDraft:
    text: str


@dataclass(frozen=True)
class Clarification:
    text: str


def validate_call(call: ToolCall) -> None:
    if not isinstance(call, ToolCall) or call.name not in TOOLS:
        raise ValueError("unknown tool")
    if not isinstance(call.arguments, dict) or set(call.arguments) != TOOLS[call.name]:
        raise ValueError("unexpected or missing tool arguments")
    if any(type(value) is not str or len(value) > 256 for value in call.arguments.values()):
        raise ValueError("arguments must be bounded strings")


def strict_json(text: str):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON field")
            result[key] = value
        return result
    return json.loads(text, object_pairs_hook=pairs)


def encode_request(request_id: str, fields: dict[str, str]) -> bytes:
    if len(fields) > 20 or any(type(v) is not str for v in fields.values()):
        raise ValueError("invalid envelope fields")
    root = ET.Element("request", protocol="1", id=request_id)
    for key, value in sorted(fields.items()):
        ET.SubElement(root, "field", name=key).text = value
    payload = ET.tostring(root, encoding="utf-8")
    if len(payload) > MAX_FRAME:
        raise ValueError("frame too large")
    return struct.pack(">I", len(payload)) + payload


def decode_response(payload: bytes, request_id: str) -> dict[str, str]:
    if len(payload) > MAX_FRAME or b"<!" in payload:
        raise ValueError("unsafe response XML")
    root = ET.fromstring(payload)
    if root.tag != "response" or root.attrib != {"protocol": "1", "id": request_id}:
        raise ValueError("wrong response envelope or correlation ID")
    if len(root) > 40:
        raise ValueError("too many response fields")
    fields = {}
    for child in root:
        if child.tag != "field" or len(child) or set(child.attrib) != {"name"}:
            raise ValueError("invalid response field")
        key = child.attrib["name"]
        if key in fields or len(key) > 64:
            raise ValueError("duplicate/oversized response field")
        fields[key] = child.text or ""
    if "code" not in fields:
        raise ValueError("response missing code")
    return fields
