import json
from wsgiref.simple_server import make_server
from .service import PaymentService

def app(service):
 def application(environ,start_response):
  method=environ.get("REQUEST_METHOD"); path=environ.get("PATH_INFO","");
  if method=="POST" and path=="/webhooks/payment":
   if environ.get("CONTENT_TYPE", "application/json").split(";", 1)[0].lower() != "application/json":
    start_response("400 Bad Request",[("Content-Type","application/json")]); return [b'{"error":"content_type"}']
   try: n=int(environ.get("CONTENT_LENGTH") or 0)
   except ValueError: n=16_385
   if n > 16_384:
    start_response("400 Bad Request",[("Content-Type","application/json")]); return [b'{"error":"payload_too_large"}']
   raw=environ["wsgi.input"].read(n); headers={"X-Signature":environ.get("HTTP_X_SIGNATURE",""),"X-Request-Id":environ.get("HTTP_X_REQUEST_ID","")}; r=service.handle(raw,headers)
  elif method=="POST" and path.startswith("/demo/replay/"):
   r=service.replay(path.split("/")[-1],environ.get("HTTP_AUTHORIZATION","").removeprefix("Bearer "))
  elif method=="GET" and path.startswith("/demo/events/"):
   data=service.store.inspect(path.split("/")[-1]); rdata=data or {"error":"not_found"}; body=json.dumps(rdata).encode(); start_response("200 OK",[("Content-Type","application/json")]); return [body]
  else: start_response("404 Not Found",[("Content-Type","application/json")]); return [b'{"error":"not_found"}']
  body=json.dumps(r.__dict__).encode(); start_response(f"{r.http_status} {'OK' if r.http_status<400 else 'Error'}",[("Content-Type","application/json")]); return [body]
 return application

def serve(service,host="127.0.0.1",port=8080): make_server(host,port,app(service)).serve_forever()
