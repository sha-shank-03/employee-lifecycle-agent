"""Exact-context synthetic Responses replay. This is protocol regression, not model evidence."""
import hashlib
from pathlib import Path
from .protocol import strict_json
from .responses import HttpReply, MAX_BODY, ProviderError, ResponsesProvider, canonical


class ReplayProvider(ResponsesProvider):
    mode = "synthetic-replay"
    def __init__(self, path):
        raw = Path(path).read_bytes()
        if len(raw) > MAX_BODY:
            raise ProviderError("replay fixture exceeds 64 KiB")
        data = strict_json(raw.decode("utf-8"))
        if type(data) is not dict or set(data) != {"schema", "provenance", "model", "turns"} \
                or data["schema"] != 1 or data["provenance"] != "authored-synthetic-not-a-model-recording" \
                or type(data["turns"]) is not list or not 1 <= len(data["turns"]) <= 24:
            raise ProviderError("explicit synthetic replay schema/provenance required")
        self.turns, self.position = data["turns"], 0
        super().__init__(data["model"], self._replay)

    def _replay(self, body):
        if self.position >= len(self.turns):
            raise ProviderError("replay exhausted")
        record = self.turns[self.position]
        if type(record) is not dict or set(record) != {"request_sha256", "response"} \
                or record["request_sha256"] != hashlib.sha256(body).hexdigest():
            raise ProviderError("synthetic replay context mismatch")
        self.position += 1
        return HttpReply(200, canonical(record["response"]))
