import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))
import pytest
from src import PaymentStore, PaymentService
from src.fixtures import body, headers
@pytest.fixture
def lab():
    store = PaymentStore()
    store.reset_demo()
    return store, PaymentService(store)
@pytest.fixture
def happy():
    raw = body()
    return raw, headers(raw)
