# Architecture

The lab is a single-process Python application backed by SQLite. The API does not store raw payment payloads. It stores event metadata and a SHA-256 payload hash.

## Transaction boundary
Order transition, event completion, and transition audit are committed together. An injected storage exception rolls back the order mutation and moves the existing event to retry or review using the recovery path.

## States
Webhook events use `received`, `processed`, `retrying`, `review`, and `rejected`. Orders begin as `pending` and may become `paid`; a pending event after paid is recorded as a conflict and never downgrades the order.

## Security
Provider authentication is HMAC-SHA256 over exact raw bytes. Operator replay uses the local synthetic token and constant-time comparison. Inspection returns metadata only. Secrets and full payloads are not logged.
