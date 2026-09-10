import hashlib
import hmac
import secrets
from datetime import datetime, timezone
from .models import PaymentEvent, ProcessResult
from .validation import verify_signature, parse_event, ValidationError, AuthenticationError, payload_hash
from .retry import MAX_ATTEMPTS, retry_time
from .state_machine import StateConflict

class PaymentService:
    def __init__(self, store, secret="sandbox-secret", operator_token="demo-admin", clock=None):
        self.store = store
        self.secret = secret.encode()
        self.operator_token = operator_token
        self.failure = None
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def request_id(self, headers):
        value = headers.get("X-Request-Id") or "req_" + secrets.token_hex(8)
        return value[:80]

    def _retry_or_review(self, event_id, request_id, reason, attempt):
        final = attempt >= MAX_ATTEMPTS
        self.store.mark_retry(event_id, request_id, attempt, reason,
                              retry_time(attempt, self.clock), final)
        return ProcessResult("review" if final else "retrying", event_id, request_id,
                             202, attempt, "event retained for review" if final else "retry scheduled")

    def _apply(self, event, request_id, attempt):
        if self.failure in ("provider_timeout", "upstream_5xx"):
            raise RuntimeError(self.failure)
        try:
            result = self.store.process(event, request_id, attempt,
                                        inject=self.failure == "partial_db_failure")
        except StateConflict as exc:
            self.store.mark_rejected(event.id, request_id, attempt, str(exc), "state_conflict")
            return ProcessResult("conflict", event.id, request_id, 409, attempt, str(exc))
        except Exception:
            raise
        return ProcessResult("processed", event.id, request_id, 202, attempt, result)

    def handle(self, raw, headers):
        request_id = self.request_id(headers)
        event_id = "unknown"
        try:
            verify_signature(raw, headers.get("X-Signature", ""), self.secret)
            event = parse_event(raw)
            event_id = event.id
            incoming_hash = payload_hash(raw)
            existing = self.store.event(event_id)
            if existing:
                if existing["payload_hash"] != incoming_hash:
                    self.store.audit(request_id, event_id, "duplicate_conflict", "payload hash mismatch", "provider")
                    self.store.db.commit()
                    return ProcessResult("rejected", event_id, request_id, 409, existing["attempt_count"], "duplicate event payload conflict")
                if existing["status"] == "processed":
                    self.store.audit(request_id, event_id, "duplicate", "already processed", "provider")
                    self.store.db.commit()
                    return ProcessResult("duplicate", event_id, request_id, 200, existing["attempt_count"], "already processed")
                attempt = existing["attempt_count"] + 1
                try:
                    return self._apply(event, request_id, attempt)
                except RuntimeError as exc:
                    return self._retry_or_review(event.id, request_id, str(exc), attempt)
                except Exception:
                    return self._retry_or_review(event.id, request_id, "partial_db_failure", attempt)
            order = self.store.order(event.order_id)
            if not order:
                raise ValidationError("missing_order", "order does not exist")
            if order["amount"] != event.amount or order["currency"] != event.currency:
                raise ValidationError("order_mismatch", "amount or currency does not match order")
            self.store.record_received(event, request_id, incoming_hash)
            try:
                return self._apply(event, request_id, 1)
            except RuntimeError as exc:
                return self._retry_or_review(event.id, request_id, str(exc), 1)
            except Exception:
                return self._retry_or_review(event.id, request_id, "partial_db_failure", 1)
        except AuthenticationError as exc:
            self.store.audit(request_id, None, "authentication_rejected", "invalid signature", "provider")
            self.store.db.commit()
            return ProcessResult("rejected", event_id, request_id, 401, 0, "invalid signature")
        except ValidationError as exc:
            self.store.audit(request_id, event_id, "validation_failed", exc.code, "provider", {"fields": exc.details.get("fields", [])})
            self.store.db.commit()
            return ProcessResult("rejected", event_id, request_id, 400, 0, exc.code)
        except RuntimeError as exc:
            existing = self.store.event(event_id)
            if existing:
                return self._retry_or_review(event_id, request_id, str(exc), existing["attempt_count"] + 1)
            return ProcessResult("rejected", event_id, request_id, 400, 0, "invalid request")

    def replay(self, event_id, token):
        request_id = "req_replay_" + secrets.token_hex(6)
        if not hmac.compare_digest(token or "", self.operator_token):
            self.store.audit(request_id, event_id, "replay_denied", "operator authorization required", "operator")
            self.store.db.commit()
            return ProcessResult("forbidden", event_id, request_id, 403, 0, "operator authorization required")
        row = self.store.event(event_id)
        if not row:
            return ProcessResult("not_found", event_id, request_id, 404, 0, "event not found")
        if row["status"] == "processed":
            self.store.audit(request_id, event_id, "manual_replay_duplicate", "already processed", "operator")
            self.store.db.commit()
            return ProcessResult("duplicate", event_id, request_id, 202, row["attempt_count"], "already processed")
        order = self.store.order(row["order_id"])
        event = PaymentEvent(event_id, row["event_type"], row["order_id"], order["amount"], order["currency"], "2026-09-10T09:00:00Z")
        self.store.audit(request_id, event_id, "manual_replay", "authorized", "operator")
        self.store.db.commit()
        try:
            result = self.store.process(event, request_id, row["attempt_count"] + 1, inject=self.failure == "partial_db_failure")
            self.store.resolve_review(event_id)
            return ProcessResult("processed", event_id, request_id, 202, row["attempt_count"] + 1, result)
        except Exception as exc:
            attempt = row["attempt_count"] + 1
            self.store.mark_retry(event_id, request_id, attempt, str(exc), "", True)
            return ProcessResult("review", event_id, request_id, 500, attempt, "event retained for review")
