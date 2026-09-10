from datetime import datetime, timedelta, timezone

MAX_ATTEMPTS = 3
RETRYABLE_REASONS = {"provider_timeout", "upstream_5xx", "partial_db_failure"}

def retryable(reason: str) -> bool:
    return reason in RETRYABLE_REASONS

def retry_time(attempt: int, clock=None) -> str:
    clock = clock or (lambda: datetime.now(timezone.utc))
    return (clock() + timedelta(seconds=attempt)).isoformat().replace("+00:00", "Z")

def run_due_retries(store, service, now=None) -> int:
    """Run due retrying events using stored metadata and the local service."""
    now = now or datetime.now(timezone.utc)
    rows = store.db.execute(
        "SELECT event_id, order_id, event_type, attempt_count, request_id, next_retry_at "
        "FROM webhook_events WHERE status='retrying'"
    ).fetchall()
    processed = 0
    for row in rows:
        due = row["next_retry_at"] is None
        if row["next_retry_at"]:
            due = datetime.fromisoformat(row["next_retry_at"].replace("Z", "+00:00")) <= now
        if not due:
            continue
        order = store.order(row["order_id"])
        if not order:
            continue
        from .models import PaymentEvent
        event = PaymentEvent(
            row["event_id"], row["event_type"], row["order_id"],
            order["amount"], order["currency"], now.isoformat().replace("+00:00", "Z")
        )
        attempt = row["attempt_count"] + 1
        try:
            result = service._apply(event, row["request_id"], attempt)
            if result.status in {"processed", "conflict"}:
                processed += 1
        except RuntimeError as exc:
            service._retry_or_review(row["event_id"], row["request_id"], str(exc), attempt)
            processed += 1
        except Exception:
            service._retry_or_review(row["event_id"], row["request_id"], "partial_db_failure", attempt)
            processed += 1
    return processed
