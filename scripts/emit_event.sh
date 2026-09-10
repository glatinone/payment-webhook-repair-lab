#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
FILE=${1:-fixtures/happy.json}
PYTHONPATH="$ROOT" python - "$ROOT/$FILE" <<'PY'
import hashlib,hmac,json,sys
from src import PaymentStore,PaymentService
raw=open(sys.argv[1],'rb').read(); s=PaymentStore('demo.sqlite3'); s.reset_demo(); svc=PaymentService(s); sig='sha256='+hmac.new(b'sandbox-secret',raw,hashlib.sha256).hexdigest(); print(json.dumps(svc.handle(raw,{'X-Signature':sig}).__dict__,indent=2))
PY
