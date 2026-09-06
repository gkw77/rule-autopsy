# Methodology — how the audit classifies your rules

This is the exact classification procedure behind every number in `../reports/`.
It encodes one borrowed idea — *A rule that claims a measurable effect without a
measurement is faith, not fact* — and applies it mechanically.

## The one question

A rules system is mostly prose, and prose is *supposed* to be prose. So the audit does not
ask "is every rule backed by data?" It asks only:

> **Of the rules that claim a measurable effect, which ones carry a receipt?**

Methodology prose ("keep functions short", "verify before acting") makes no metric claim and
is out of scope — flagged `behavior` (N/A). Only blocks that assert an effect
("cuts cost", "reduces false blocks", "intercepts X%") enter the verdict ladder.

## Verdict ladder

For each block that claims an effect:

| verdict | condition | meaning |
|---|---|---|
| `selftested` | claims an effect **and** a number **and** an unambiguous "we ran it" marker | I ran it. (Partial — N≥10 / agentic runs still recommended.) |
| `secondhand` | claims an effect + a number, but the number is cited from a source (no "we ran" marker) | Reproducible, but not reproduced here. |
| `faith` | claims an effect + a number, no marker, no source | Asserts a number with zero receipt. |
| `claimNoMetric` | claims an effect, gives no number | The effect may be real — there is just nothing to check. |

Everything else → `behavior` (out of scope).

## Two detectors

1. **rule-quality-audit.js** — the whole-file health scan: per block, does it carry a
   machine-checkable verify signal, cite evidence, cite a source, or is it prose? Also flags
   placeholder cop-outs (`TBD`, "add appropriate error handling") and hedge language.
2. **rule-evidence-audit.js** — the claim×receipt verdict ladder above.

Both split files at `##`/`###` headings, strip fenced + inline code (so quoted anti-patterns
don't false-positive), and output structured JSON.

## Honest limits (read before citing any number)

1. **Regex ≠ understanding.** Detectors cannot perfectly separate "they measured" from "I
   measured." `selftested` here is a *flag to triage*, not a certificate — manual review is
   the backstop. (See REPORT section 3: two of seven "selftested" flags on the real corpus
   were the audit describing itself.)
2. **Claim-detector strictness moves the ratio.** A narrower definition of "claims an effect"
   flags fewer blocks; a broader one flags more. On the committed corpus this moved the
   unproven ratio from 79% to 86% without changing the direction. Always state which detector
   and quote a range.
3. **Behavior ≠ bad.** 78% prose is expected and correct for a rules system. Only the
   *effect-claiming minority* is held to the evidence bar.
4. **Numbers are for YOUR corpus.** The committed report holds aggregate numbers from a
   private corpus. Anyone can reproduce the *method* on their own rules in one command; nobody
   can reproduce our exact numbers without our corpus. That is the honest ceiling.

## Reproduction

```
node verify-claims/verify-claims.js                          # demo fixture (public)
node verify-claims/verify-claims.js --self-corpus <dir>      # your own rules
```

Receipts that need a live key or your session dir are documented in `../receipts/` and
skipped by the runner rather than silently dropped.
