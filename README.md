# rule-autopsy

**I autopsied my own agent-rules system against its own most important rule.**

My rulebase contains a rule that says: *a rule that isn't measured is faith, not fact.*
So I ran that rule on the rulebase itself.

**Result: 86% of my rules' effect-claims were never measured. My own honesty rule
convicted my own rules.**

The method re-runs on any rules directory in one command — including yours:

```
node verify-claims/verify-claims.js --self-corpus <your-rules-dir>
```

The 86% itself is from a private corpus (only aggregate numbers are published). Two of the
receipts that did measure something reproduce byte-for-byte in this repo; see `receipts/`.
Read `docs/METHODOLOGY.md` before quoting any number.

## The finding

I maintain a 7-stage rules system for agent work (~210 markdown blocks). It tells agents to
measure before they claim, to carry receipts, to treat unmeasured claims as faith.

I scanned it with the same standard. Of **50 blocks that claim a measurable effect**
("cuts cost", "reduces false blocks", "intercepts X%"):

| verdict | count |
|---|---|
| measured — has a number *and* "we ran it" | 7 |
| cited from someone else — reproducible, not reproduced | 7 |
| **claimed a number with no receipt at all** | 2 |
| **claimed an effect with no number to check** | 34 |
| **unproven, total** | **43 / 50 — 86%** |

The system is 78% prose by design — that part is fine; a rules system is supposed to be
prose. The indictment is narrower and sharper: **of the blocks that promise an effect,
86% never prove it.** And that 86% is a floor, because manual triage of the 7 "measured"
flags shows at least 2 are the audit describing itself, not real rigs.

## This is the honest part that makes it worth reading

Two of the receipts reproduce **exactly today** (output matched the committed report line for line), deterministically, offline:

```
cd receipts/gzh-rig && python rig.py
# 19 seeded defects → double gate 19/19 (100%), best single gate 17/19 (89%), +2/19

cd receipts/agent-chief-rig && python scripts/readme_metrics.py
# 24 events → 96% intercepted, 75% reach LLM, 70% cache-hit, $0.104/1k
```

Three more receipts are documented with their exact limits (one needs a live model key,
two need your own `~/.claude` session dir) — none are silently skipped.

## What this is

Two pieces:

1. **A confession, committed.** `reports/REPORT-2026-09-04.md` is the audit of a real rules
   system that was designed to be honest and is, by its own standard, mostly faith. Aggregate
   numbers only — the rule content stays private. That boundary is deliberate.

2. **A tool you run on yourself.** `verify-claims/` audits any directory of markdown rules and
   prints the same verdict ladder. Not "do you have rules?" — *of the rules that promise
   something, how many can you prove?*

```
node verify-claims/verify-claims.js                 # ships with a demo corpus
node verify-claims/verify-claims.js --self-corpus . # your CLAUDE.md / rules
```

## What this does NOT claim

- The 160 methodology blocks are not "bad." Prose is the point.
- No specific rule is proven *wrong* or dead weight. Measuring per-rule catch-rate and
  false-block-rate — the "which rules actually earn their tokens" experiment — needs an
  incident-regression harness. That is the roadmap, not this report.
- The ratio moves with claim-detector strictness (79–86% on this corpus). The direction
  does not. See `docs/METHODOLOGY.md` before quoting any number.

## Roadmap

- **Incident-regression harness**: feed a real past-failure log into the rule system and
  measure, per rule, which failures it catches and which safe actions it blocks. This is the
  way to an honest *dead-weight* number — the finding every rules repo claims and none shows.
- **Corpus snapshot tooling**: commit a sanitized corpus so the exact headline is
  third-party-reproducible, not just the method.

## Docs

- `docs/METHODOLOGY.md` — exact classification rules + honest limits
- `receipts/README.md` — the five receipts, what each proves and doesn't
- `reports/` — committed audit reports

## License

MIT
