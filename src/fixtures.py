import hashlib, hmac, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def body(name="happy.json"):
    return (ROOT / "fixtures" / name).read_bytes()
def signature(raw, secret=b"sandbox-secret"):
    return "sha256=" + hmac.new(secret, raw, hashlib.sha256).hexdigest()
def headers(raw, request_id="req_test"):
    return {"X-Signature": signature(raw), "X-Request-Id": request_id}
