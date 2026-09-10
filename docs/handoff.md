# Handoff

1. Copy `.env.example` to a local environment file and replace placeholders only for local testing.
2. Run `python -m pytest -q`.
3. Run `scripts/reset_demo.sh`, then `scripts/emit_event.sh`.
4. Inspect the SQLite event timeline using the API or Python REPL.
5. Use the failure fixtures to demonstrate retry and review behavior.

Production adaptation would replace the local secret source, database, clock, queue, and provider adapter after a separate security and operational review. Those integrations are deliberately outside this MVP.
