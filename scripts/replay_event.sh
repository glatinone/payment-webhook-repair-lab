#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHONPATH="$ROOT" python - "$1" <<'PY'
import sys,json
from src import PaymentStore,PaymentService
s=PaymentStore('demo.sqlite3'); print(json.dumps(PaymentService(s).replay(sys.argv[1],'demo-admin').__dict__,indent=2))
PY
