"""Single loopback HTTP attempt. Spawned only in separately leased tests/runs."""
import base64
import json
import socket
import sys
import urllib.error
import urllib.parse
import urllib.request

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

def main():
    raw = sys.stdin.buffer.read(180000)
    value = json.loads(raw)
    p = urllib.parse.urlsplit(value["endpoint"])
    if p.scheme != "http" or p.hostname != "127.0.0.1" or p.path != "/v1/chat/completions" or p.username or p.password or p.query or p.fragment:
        return 1
    body = base64.b64decode(value["body"], validate=True)
    if len(body) > 131072:
        return 1
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    req = urllib.request.Request(value["endpoint"], data=body, method="POST", headers={"Content-Type": "application/json"})
    try:
        with opener.open(req, timeout=15) as response:
            if response.headers.get_content_type() != "application/json":
                return 1
            reply = response.read(65537)
            if len(reply) > 65536:
                return 1
            result = {"status": response.status, "body": base64.b64encode(reply).decode()}
    except urllib.error.HTTPError as error:
        result = {"status": error.code, "body": ""}
    sys.stdout.write(json.dumps(result, separators=(",", ":")))
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (TimeoutError, socket.timeout):
        raise SystemExit(2)
    except urllib.error.URLError as error:
        raise SystemExit(2 if isinstance(error.reason, (TimeoutError, socket.timeout)) else 1)
    except Exception:
        raise SystemExit(1)
