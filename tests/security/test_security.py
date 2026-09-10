from src.fixtures import body,headers

def test_secret_and_payload_are_not_exposed(lab):
    store,service=lab; raw=body(); r=service.handle(raw,{"X-Signature":"sha256=wrong","X-Request-Id":"req_security"}); assert "sandbox-secret" not in r.message; assert store.inspect("evt_001") is None

def test_replay_authorization_is_constant_time_boundary(lab,happy):
    store,service=lab; raw,head=happy; service.handle(raw,head); r=service.replay("evt_001","not-demo-admin"); assert r.http_status==403; assert store.order("ord_001")["status"]=="paid"

def test_duplicate_payload_conflict_is_not_mutating(lab,happy):
    store,service=lab; raw,head=happy; service.handle(raw,head); changed=raw.replace(b"1500",b"1400"); r=service.handle(changed,headers(changed)); assert r.http_status==409; assert store.order("ord_001")["status"]=="paid"
