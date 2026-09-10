import hashlib, hmac, json, re
from datetime import datetime
from .models import PaymentEvent

class ValidationError(Exception):
    def __init__(self, code: str, message: str, details: dict | None = None):
        super().__init__(message); self.code = code; self.details = details or {}

class AuthenticationError(Exception): pass

_ID = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")

def verify_signature(raw_body: bytes, header: str, secret: bytes) -> None:
    if not header or not header.startswith("sha256="):
        raise AuthenticationError("invalid signature")
    supplied = header[7:]
    expected = hmac.new(secret, raw_body, hashlib.sha256).hexdigest()
    if len(supplied) != len(expected) or not hmac.compare_digest(supplied, expected):
        raise AuthenticationError("invalid signature")

def parse_event(raw_body: bytes, max_bytes: int = 16_384) -> PaymentEvent:
    if len(raw_body) > max_bytes: raise ValidationError("payload_too_large", "payload exceeds limit")
    try: data = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError): raise ValidationError("invalid_json", "body must be valid JSON")
    if not isinstance(data, dict): raise ValidationError("invalid_schema", "body must be an object")
    required = ("id", "type", "order_id", "amount", "currency", "occurred_at")
    missing = [x for x in required if x not in data]
    if missing: raise ValidationError("required_fields", "required fields are missing", {"fields": missing})
    if any(not isinstance(data[x], str) for x in ("id", "type", "order_id", "currency", "occurred_at")):
        raise ValidationError("invalid_schema", "string fields have invalid types")
    if not isinstance(data["amount"], int) or isinstance(data["amount"], bool) or data["amount"] <= 0:
        raise ValidationError("invalid_amount", "amount must be a positive integer")
    if data["type"] not in ("payment.pending", "payment.paid"): raise ValidationError("invalid_type", "unsupported event type")
    if not _ID.fullmatch(data["id"]) or not _ID.fullmatch(data["order_id"]): raise ValidationError("invalid_identifier", "invalid identifier")
    if len(data["currency"]) != 3 or data["currency"] != data["currency"].upper(): raise ValidationError("invalid_currency", "currency must be uppercase ISO-like code")
    try: datetime.fromisoformat(data["occurred_at"].replace("Z", "+00:00"))
    except ValueError: raise ValidationError("invalid_timestamp", "occurred_at must be ISO-8601")
    return PaymentEvent(data["id"], data["type"], data["order_id"], data["amount"], data["currency"], data["occurred_at"])

def payload_hash(raw_body: bytes) -> str: return hashlib.sha256(raw_body).hexdigest()
