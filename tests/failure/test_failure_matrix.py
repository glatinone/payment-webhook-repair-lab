import json
from src.fixtures import body, headers

def send(service, name="happy.json", request_id="req_failure"):
    raw=body(name); return service.handle(raw,headers(raw,request_id))

def test_timeout_retries(lab):
    store,service=lab; service.failure="provider_timeout"
    r=send(service,"failures/timeout.json"); assert r.status=="retrying" and r.attempts==1
    r=send(service,"failures/timeout.json"); assert r.attempts==2
    r=send(service,"failures/timeout.json"); assert r.status=="review" and store.event("evt_timeout")["status"]=="review"

def test_duplicate_is_idempotent(lab):
    store,service=lab; assert send(service).status=="processed"; r=send(service); assert r.http_status==200; assert store.order("ord_001")["status"]=="paid"

def test_invalid_signature(lab,happy):
    store,service=lab; raw,head=happy; head["X-Signature"]="sha256=bad"; r=service.handle(raw,head); assert r.http_status==401; assert store.event("evt_001") is None

def test_malformed_payload(lab):
    store,service=lab; r=send(service,"malformed.json"); assert r.http_status==400; assert store.order("ord_001")["status"]=="pending"

def test_required_fields(lab):
    store,service=lab; raw=b'{"id":"evt_missing","type":"payment.paid","order_id":"ord_001","currency":"USD","occurred_at":"2026-09-10T09:00:00Z"}'; from src.fixtures import headers; r=service.handle(raw,headers(raw)); assert r.http_status==400

def test_upstream_failure(lab):
    store,service=lab; service.failure="upstream_5xx"; r=send(service,"failures/upstream_5xx.json"); assert r.status=="retrying"; assert store.order("ord_001")["status"]=="pending"

def test_partial_db_failure(lab):
    store,service=lab; service.failure="partial_db_failure"; r=send(service,"failures/partial_db_failure.json"); assert r.status=="retrying"; assert store.order("ord_001")["status"]=="pending"; assert store.event("evt_partial_db_failure")["status"]=="retrying"

def test_out_of_order_state(lab):
    store,service=lab; assert send(service).status=="processed"; raw=json.dumps({"id":"evt_pending","type":"payment.pending","order_id":"ord_001","amount":1500,"currency":"USD","occurred_at":"2026-09-10T09:01:00Z"}).encode(); r=service.handle(raw,headers(raw)); assert r.http_status==409; assert store.order("ord_001")["status"]=="paid"

def test_retry_exhaustion_and_review_recovery(lab):
    store,service=lab; service.failure="upstream_5xx"; name="failures/upstream_5xx.json"
    for _ in range(3): r=send(service,name)
    assert r.status=="review"; service.failure=None; r=service.replay("evt_upstream_5xx","demo-admin"); assert r.status=="processed"; assert store.order("ord_001")["status"]=="paid"
