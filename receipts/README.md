# Receipts — the measured core

A rule that claims a measurable effect should carry a receipt: a command that re-runs the measurement. These five are the receipts behind the aggregate numbers in `../reports/`. Two reproduce deterministically and offline right here; two need your own `~/.claude` session dir; one needs a live model API key.

| # | Receipt | Measures | Runs here? | Key number |
|---|---------|----------|-----------|-----------|
| 1 | `gzh-rig/` | dual-gate (source + product) lint capture beats either single gate | ✅ offline, deterministic | 19/19 vs 17/19 vs 12/19 |
| 2 | `agent-chief-rig/` | worthiness-gate cascade metrics (deterministic demo replay) | ✅ offline, deterministic | 96% intercept, 75% reach-LLM, 70% cache-hit |
| 3 | `dao-cache-rig-ark.py` | stable-prefix prompt caching A/B (N=10) | ⚠️ needs live model key | median 95.9% vs 0% |
| 4 | `mcp-audit-rig.py` | MCP servers available ≠ called (read-only session scan) | ⚠️ needs `~/.claude/projects` | 3/3 configured, 0 calls |
| 5 | `post-verify-edit-rig.py` | edits-after-last-verify signal is extractable | ⚠️ needs `~/.claude/projects` | 70% sessions keep editing post-verify |

Honest note on what these do *and don't* prove is in each section and in `../docs/METHODOLOGY.md`.

---

## 1. gzh-rig — dual-gate beats single-gate

Seeding 19 known HTML defects into a WeChat-article pipeline, which gate catches them?

```
cd receipts/gzh-rig && python rig.py
```

- source-only gate: **12/19 (63%)** — lints the component library / tokens
- product-only gate: **17/19 (89%)** — validates the final rendered HTML
- double gate: **19/19 (100%)**, +2/19 (11%) over the best single gate
- expectation mismatches: **0**

Deterministic regex lint, so N=1 is valid (no sampling variance). Limit: proves the gates are structurally nested (union ⊇ each), not a real article-failure escape rate.

## 2. agent-chief-rig — worthiness-gate metrics, reproduced

Replaying agent-chief's own 24-event demo through a fixture judge and price table:

```
cd receipts/agent-chief-rig && python scripts/readme_metrics.py
```

- 24 events in → 1 interruption (**96% intercepted**: 14 blocked outright)
- **75%** of events ever reach the LLM (noisiest 25% dies on free hard rules)
- stable-prefix prompts: **70%** judge-input cache-hit
- projected cost **$0.104 per 1,000 events**

This is a *reproduction* receipt — it verifies the cited numbers are real and re-derivable, it does not independently measure our own worthiness gate.

Vendored: a minimal subset of [`smile-pinai/agent-chief`](https://github.com/smile-pinai/agent-chief) (MIT, © 2026 SmileLikeYe) — only the modules `scripts/readme_metrics.py` needs to run. License in `agent-chief-rig/LICENSE`. Full upstream kept upstream.

## 3. dao-cache-rig-ark.py — cache stability A/B (needs live key)

A/B: stable system-prefix vs volatile-prefix across N=10 model calls, measuring cache_read fraction.

```
# requires a live ANTHROPIC_AUTH_TOKEN / ARK key with cache_control support
python dao-cache-rig-ark.py
```

- A stable prefix: **median 95.9%** cache-read (10 × 96%)
- B drift prefix: **median 0%** (10 × 0%)
- delta **+95.9%**, GATE PASS

Ran 2026-07-14 (glm-5.2 via ARK). Not re-run in this repo's CI because it needs a paid key. The original rig had a drift bug (volatile appended to the *tail* doesn't break a prefix match → false pass); this version injects volatility into the prefix.

## 4. mcp-audit-rig.py — available ≠ called (needs session dir)

Read-only scan of your own `~/.claude/projects/**/*.jsonl`, aggregating tool_use counts. No content is printed or stored.

```
python mcp-audit-rig.py            # point at your projects dir
```

- 3/3 configured MCP servers had **zero** calls across 167 sessions (pure schema-token tax)
- top 20% of tools (5/26) account for **87%** of calls (Pareto tail = waste candidates)

Limit: premise measurement (static counts overstate load), not a full "trimming is safe" A/B.

## 5. post-verify-edit-rig.py — edits after last verify (needs session dir)

Read-only scan extracting the last-verify → subsequent-edit signal from your session logs.

```
python post-verify-edit-rig.py     # point at your projects dir
```

- **70.4%** (19/27) of sessions that verify keep editing afterward (median 3 edits)
- 157 / 2200 edits land after the last verify = **7.1% unverified-work ratio**

Limit: verify detection is heuristic; "post-verify edit" ≠ "post-verify bug" (could be benign cleanup). Proves the signal is extractable, not its correlation with bugs.
