"""Bounded harness-owned crash packet reader; these files never enter actor context."""
from pathlib import Path
from agent.protocol import strict_json


def read_packets(path):
    raw = Path(path).read_bytes()
    if len(raw) > 65_536:
        raise ValueError("recovery evidence exceeds 64 KiB")
    value = strict_json(raw.decode("utf-8"))
    if type(value) is not dict or set(value) != {"packets"} or type(value["packets"]) is not list:
        raise ValueError("invalid recovery packet container")
    return value["packets"]
