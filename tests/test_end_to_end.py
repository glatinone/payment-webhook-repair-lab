from src.fixtures import body,headers

def test_complete_demo_flow(lab):
    store,service=lab; raw=body(); assert service.handle(raw,headers(raw)).status=="processed"; assert service.handle(raw,headers(raw,"req_duplicate")).status=="duplicate"; service.failure="provider_timeout"; fail=body("failures/timeout.json"); service.handle(fail,headers(fail)); service.failure=None; assert service.replay("evt_timeout","demo-admin").status=="processed"; inspection=store.inspect("evt_timeout"); assert len(inspection["timeline"]) >= 2
