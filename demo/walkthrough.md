# Demo walkthrough

1. Explain the risk of duplicate orders and silent payment failures.
2. Reset the local database.
3. Emit `fixtures/happy.json` and show `processed`, order `paid`, attempt 1, and the audit timeline.
4. Emit the same fixture again and show HTTP 200 duplicate no-op.
5. Set the local failure switch to timeout in a Python REPL, send the timeout fixture three times, and show `review`.
6. Clear the switch and replay with `demo-admin` to recover the order.
7. Send a bad signature and malformed fixture to show 401 and 400 before persistence.
8. Send pending after paid to show 409 with no downgrade.
9. Run the full test suite and show the nine failure tests plus security and end-to-end checks.
10. Map the synthetic provider, order store, queue, and audit output to the client's stack.
