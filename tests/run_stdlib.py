"""Dependency-free runner for the pytest-shaped deterministic test plan."""
import inspect, sys, traceback, types
from contextlib import contextmanager
from pathlib import Path

class _RaisesInfo:
    value = None
    def __init__(self, expected): self.expected = expected
    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb):
        if exc_type is None: raise AssertionError(f"expected {self.expected.__name__} to be raised")
        if not issubclass(exc_type, self.expected): return False
        self.value = exc
        return True

def _raises(expected): return _RaisesInfo(expected)

pytest_stub = types.ModuleType("pytest")
pytest_stub.raises = _raises
sys.modules.setdefault("pytest", pytest_stub)
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src import PaymentStore, PaymentService
from src.fixtures import body, headers

def make_lab():
    store = PaymentStore(); store.reset_demo(); return store, PaymentService(store)
def make_happy():
    raw = body(); return raw, headers(raw)
def call(fn):
    sig = inspect.signature(fn); args=[]; lab=None; happy=None
    if "lab" in sig.parameters:
        lab=make_lab(); args.append(lab)
    if "happy" in sig.parameters:
        happy=make_happy(); args.append(happy)
    return fn(*args)

def main():
    files = sorted(Path(__file__).parent.rglob("test_*.py"))
    tests=[]
    for path in files:
        if path.name == "run_stdlib.py": continue
        ns={"__name__": path.stem, "__file__": str(path)}
        exec(compile(path.read_text(), str(path), "exec"), ns)
        tests.extend((path, name, fn) for name,fn in ns.items() if name.startswith("test_") and callable(fn))
    passed=failed=0
    for path,name,fn in tests:
        try:
            call(fn); passed += 1; print(f"PASS {path.relative_to(ROOT)}::{name}")
        except Exception:
            failed += 1; print(f"FAIL {path.relative_to(ROOT)}::{name}"); traceback.print_exc()
    print(f"SUMMARY passed={passed} failed={failed} total={len(tests)}")
    return 1 if failed else 0
if __name__ == "__main__": raise SystemExit(main())
