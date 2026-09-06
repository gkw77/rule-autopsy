# Demo: rules that claim effects

Each block below makes a *metric claim*. The evidence audit will label it selftested / secondhand / faith / claimNoMetric so you can see the classification in action.

## 05. Stable prompt prefix

Keeping the system + context prefix byte-identical across calls cuts cost dramatically.

We ran our own rig: N=10, stable-prefix median cache-read 95.9% vs drifting-prefix median 0%, delta +95.9%. Repro: `python receipts/dao-cache-rig-ark.py`.

## 06. Dual-gate validation

Validating both the source component library and the final rendered artifact catches more than either gate alone.

We ran our own rig: 19 seeded defects, product-only gate caught 17/19 (89%), double gate 19/19 (100%), +2/19 over the best single gate. Repro: `cd receipts/gzh-rig && python rig.py`.

## 07. Worthiness gate

agent-chief reports its cascade intercepts 96% of 24 events (14 blocked outright), and only 75% of events ever reach the LLM. Reproduced from its demo replay.

## 08. Daily digest

Sending a daily digest reduces context churn by about 40% and improves session focus.

## 09. Retry budget

Give every flaky external call exactly 3 retries with backoff; this removes most intermittent failures in practice.

## 10. Idempotent migrations

Rewrite migrations to be idempotent; rerunning improves safety on every deploy, so outages recover faster.
