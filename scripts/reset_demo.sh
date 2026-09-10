#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHONPATH="$ROOT" python -c 'from src import PaymentStore; s=PaymentStore("demo.sqlite3"); s.reset_demo(); print("demo reset")'
