import json
from src.api import app
from io import BytesIO

def request(service, method, path, body=b"", headers=None):
    headers=headers or {}
    env={"REQUEST_METHOD":method,"PATH_INFO":path,"CONTENT_LENGTH":str(len(body)),"wsgi.input":BytesIO(body),"HTTP_X_SIGNATURE":headers.get("X-Signature", ""),"HTTP_X_REQUEST_ID":headers.get("X-Request-Id", ""),"HTTP_AUTHORIZATION":headers.get("Authorization", "")}
    result={}
    def start(status, hdrs): result["status"]=int(status.split()[0]); result["headers"]=hdrs
    result["body"]=b"".join(app(service)(env,start))
    return result

def test_http_happy_and_inspection(lab,happy):
    store,service=lab; raw,headers=request_body=happy
    r=request(service,"POST","/webhooks/payment",raw,headers)
    assert r["status"] == 202
    r=request(service,"GET","/demo/events/evt_001")
    data=json.loads(r["body"]); assert data["event"]["status"] == "processed"

def test_http_replay_requires_operator(lab,happy):
    store,service=lab; raw,headers=happy
    request(service,"POST","/webhooks/payment",raw,headers)
    assert request(service,"POST","/demo/replay/evt_001",headers={"Authorization":"Bearer wrong"})["status"] == 403
    assert request(service,"POST","/demo/replay/evt_001",headers={"Authorization":"Bearer demo-admin"})["status"] == 202
