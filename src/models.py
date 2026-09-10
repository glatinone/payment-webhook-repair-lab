from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class PaymentEvent:
    id: str
    type: str
    order_id: str
    amount: int
    currency: str
    occurred_at: str

@dataclass(frozen=True)
class ProcessResult:
    status: str
    event_id: str
    request_id: str
    http_status: int
    attempts: int
    message: str

@dataclass(frozen=True)
class EventInspection:
    event: dict[str, Any]
    timeline: list[dict[str, Any]]
    review: dict[str, Any] | None
