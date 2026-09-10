import json, sqlite3
from datetime import datetime, timezone
from .models import PaymentEvent

def now(): return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

class PaymentStore:
    def __init__(self, path=":memory:"):
        self.path = path; self.db = sqlite3.connect(path, check_same_thread=False); self.db.row_factory = sqlite3.Row; self.init_schema()
    def init_schema(self):
        self.db.executescript('''CREATE TABLE IF NOT EXISTS orders(id TEXT PRIMARY KEY,status TEXT NOT NULL,amount INTEGER NOT NULL,currency TEXT NOT NULL,updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS webhook_events(event_id TEXT PRIMARY KEY,order_id TEXT NOT NULL,event_type TEXT NOT NULL,payload_hash TEXT NOT NULL,status TEXT NOT NULL,attempt_count INTEGER NOT NULL DEFAULT 0,request_id TEXT NOT NULL,last_error TEXT,next_retry_at TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS audit_events(id INTEGER PRIMARY KEY AUTOINCREMENT,request_id TEXT,event_id TEXT,action TEXT,result TEXT,actor TEXT,metadata_json TEXT,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS review_queue(event_id TEXT PRIMARY KEY,reason TEXT NOT NULL,created_at TEXT NOT NULL,resolved_at TEXT);
        '''); self.db.commit()
    def reset_demo(self):
        self.db.executescript("DELETE FROM review_queue; DELETE FROM audit_events; DELETE FROM webhook_events; DELETE FROM orders;")
        t=now(); self.db.execute("INSERT INTO orders VALUES(?,?,?,?,?)",("ord_001","pending",1500,"USD",t)); self.db.commit()
    def close(self): self.db.close()
    def order(self, order_id): return self.db.execute("SELECT * FROM orders WHERE id=?",(order_id,)).fetchone()
    def event(self, event_id): return self.db.execute("SELECT * FROM webhook_events WHERE event_id=?",(event_id,)).fetchone()
    def record_received(self,e,request_id,ph):
        t=now(); self.db.execute("INSERT INTO webhook_events(event_id,order_id,event_type,payload_hash,status,attempt_count,request_id,last_error,next_retry_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(e.id,e.order_id,e.type,ph,"received",0,request_id,None,None,t,t)); self.db.commit()
    def audit(self, request_id,event_id,action,result,actor,metadata=None, conn=None):
        c=conn or self.db; c.execute("INSERT INTO audit_events(request_id,event_id,action,result,actor,metadata_json,created_at) VALUES(?,?,?,?,?,?,?)",(request_id,event_id,action,result,actor,json.dumps(metadata or {},sort_keys=True),now()))
    def process(self,e,request_id,attempt,inject=False):
        from .state_machine import transition, StateConflict
        c=self.db; c.execute("BEGIN")
        try:
            order=c.execute("SELECT * FROM orders WHERE id=?",(e.order_id,)).fetchone()
            if not order: raise ValueError("order not found")
            if order["amount"] != e.amount or order["currency"] != e.currency: raise ValueError("order amount or currency mismatch")
            new_status,result=transition(order["status"],e.type)
            if result == "ignored_stale":
                from .state_machine import StateConflict
                raise StateConflict("stale pending event cannot downgrade paid order")
            c.execute("UPDATE orders SET status=?,updated_at=? WHERE id=?",(new_status,now(),e.order_id))
            if inject: raise sqlite3.OperationalError("simulated partial database failure")
            c.execute("UPDATE webhook_events SET status='processed',attempt_count=?,updated_at=?,last_error=NULL WHERE event_id=?",(attempt,now(),e.id))
            self.audit(request_id,e.id,"state_transition",result,"worker",{"from":order["status"],"to":new_status},c); c.commit(); return result
        except Exception:
            c.rollback(); raise
    def mark_rejected(self, event_id, request_id, attempt, error, action):
        self.db.execute("UPDATE webhook_events SET status='rejected',attempt_count=?,last_error=?,updated_at=? WHERE event_id=?", (attempt, error, now(), event_id))
        self.audit(request_id, event_id, action, error, "worker", {"attempt": attempt})
        self.db.commit()
    def resolve_review(self, event_id):
        self.db.execute("UPDATE review_queue SET resolved_at=? WHERE event_id=?", (now(), event_id))
        self.db.commit()
    def mark_retry(self,event_id,request_id,attempt,error,next_retry,final=False):
        status="review" if final else "retrying"; t=now(); self.db.execute("UPDATE webhook_events SET status=?,attempt_count=?,last_error=?,next_retry_at=?,updated_at=? WHERE event_id=?",(status,attempt,error,next_retry,t,event_id)); self.audit(request_id,event_id,"review_required" if final else "retry_scheduled",error,"worker",{"attempt":attempt});
        if final: self.db.execute("INSERT OR REPLACE INTO review_queue(event_id,reason,created_at) VALUES(?,?,?)",(event_id,error,t))
        self.db.commit()
    def timeline(self,event_id): return [dict(x) for x in self.db.execute("SELECT * FROM audit_events WHERE event_id=? ORDER BY id",(event_id,))]
    def inspect(self,event_id):
        e=self.event(event_id)
        if not e:return None
        review=self.db.execute("SELECT * FROM review_queue WHERE event_id=?",(event_id,)).fetchone()
        return {"event":dict(e),"timeline":self.timeline(event_id),"review":dict(review) if review else None}
