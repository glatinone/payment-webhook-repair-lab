class StateConflict(Exception): pass

def transition(current: str, event_type: str) -> tuple[str, str]:
    if current == "pending" and event_type == "payment.paid": return "paid", "transitioned"
    if current == "pending" and event_type == "payment.pending": return "pending", "accepted"
    if current == "paid" and event_type == "payment.paid": return "paid", "already_paid"
    if current == "paid" and event_type == "payment.pending": return "paid", "ignored_stale"
    raise StateConflict(f"cannot apply {event_type} to {current}")
