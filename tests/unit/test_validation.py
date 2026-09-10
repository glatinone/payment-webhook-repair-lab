import json, hmac, hashlib
import pytest
from src.validation import parse_event, verify_signature, ValidationError, AuthenticationError
from src.state_machine import transition, StateConflict

def test_signature_uses_raw_body():
    raw=b'{"id":"evt"}'
    sig="sha256="+hmac.new(b"sandbox-secret",raw,hashlib.sha256).hexdigest()
    verify_signature(raw,sig,b"sandbox-secret")
    with pytest.raises(AuthenticationError): verify_signature(raw+b" ",sig,b"sandbox-secret")

def test_schema_rejects_malformed_and_limits():
    with pytest.raises(ValidationError) as e: parse_event(b'{"id":"x"}')
    assert e.value.code == "required_fields"
    with pytest.raises(ValidationError) as e: parse_event(b"x"*17000)
    assert e.value.code == "payload_too_large"

def test_state_machine():
    assert transition("pending","payment.paid") == ("paid","transitioned")
    assert transition("paid","payment.pending") == ("paid","ignored_stale")
    with pytest.raises(StateConflict): transition("failed","payment.paid")
