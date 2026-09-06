# Demo: hooks, including the anti-patterns the quality audit flags

## 11. PreToolUse hook on destructive commands

Before any `rm -rf`, `git push --force`, or `drop table`, block and ask. Gate check: `summary.errors > 0` → BLOCK.

## 12. PostToolUse log scrub

Make sure API keys don't reach the transcript. If a tool output looks key-shaped, redact it before it is stored.

## 13. Webhook retry — TODO

For webhook delivery, add appropriate error handling, retry with exponential backoff, and fill in details of the circuit breaker later. Handle edge cases around partial failures.

## 14. Idle callback

When the queue is idle, usually fire the callback every few seconds; generally a 5-second poll is fine, though a shorter interval probably isn't worth the load.
