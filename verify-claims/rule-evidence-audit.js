#!/usr/bin/env node
// rule-evidence-audit.js — classify rule blocks by claim × evidence receipt (A4 applied to yourself).
//
//   Usage:  node rule-evidence-audit.js [corpus-root]
//
//   corpus-root  Directory of markdown rules to audit (walked recursively).
//                Defaults to ../fixtures/rules.
//
// A4 says: only rules that CLAIM a measurable effect need evidence; methodology prose is N/A.
// Each block that makes an effect/measurement claim is classified:
//   selftested     claims an effect WITH a number AND an unambiguous "I ran it" marker
//   secondhand     cites a source repo's number (reproducible, but not reproduced here)
//   faith          claims a number with no receipt at all
//   claimNoMetric  claims an effect but gives no number to check
// Everything else is behavior (methodology prose; no metric claim) and is out of scope.
//
// Honest limits (v1): regex cannot perfectly separate "they measured" from "I measured";
// "self-tested" here is partial and may over-count — manual triage is the backstop.

const fs = require('fs'), path = require('path');
const corpusRoot = path.resolve(process.argv[2] || path.join(__dirname, '..', 'fixtures', 'rules'));

function walk(dir, acc = []) {
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, ent.name);
    if (ent.isDirectory()) walk(p, acc);
    else if (ent.name.toLowerCase().endsWith('.md')) acc.push(p);
  }
  return acc;
}
function stripCode(t) { return t.replace(/```[\s\S]*?```/g, ' ').replace(/`[^`\n]*`/g, ' '); }

// Claims an effect/measurement improvement (narrow: effect verbs, not scope words).
const CLAIM = /reduc|improv|speed up|faster|boost|savings?|intercept|hit rate|cache-?hit|reach.{0,6}LLM|false.{0,6}rate|cost|drift|early-?exit|monotonic|no-op.{0,6}short|catch(?:es|ed)? more|cut|省|降低|减少|提升|提高|缩短|加速|拦截|误判|捕获率|缺陷率|多抓/i;
// A concrete number (percent / x / k / runs / ms / $).
const NUMBER = /\$\d|\d+(?:\.\d+)?\s*(?:%|x|×|倍|k\b|runs?|t\/s|ms)|N\s*=\s*\d+/i;
// Unambiguous "I ran it" markers.
const SELF_STRONG = /I ran|I ran it|we ran|our rig|own rig|self-tested|single-shot|self-tested|primed-eyes|promptfoo|N\s*runs|median over|rig\s*00[12]|自测|我.{0,4}跑/i;
// Weak "measured" — usually a citation to someone else's number -> secondhand.
const SELF_WEAK = /measured|reproduc|verify-claims|make .{0,8}metrics|agentic|benchmark|实测|复算/i;
// Cites a source repo / author.
const SOURCE = /(?:from|via|inspired by)\s+\S+|agent-chief|dao-code|ponytail|engram|gzh|merge-queue|openwiki|loopy|fable|openscience|T3MP3ST|TestSprite|exploitarium|dzhng|cognitive-core|MiMo-Code|cloudflare|BuilderIO|obra|affaan|来自/i;

const rows = [];
const counts = { behavior: 0, secondhand: 0, selftested: 0, faith: 0, claimNoMetric: 0, total: 0 };

for (const file of walk(corpusRoot)) {
  const rel = path.relative(corpusRoot, file);
  const lines = fs.readFileSync(file, 'utf8').split('\n');
  let cur = null; const blocks = [];
  for (const ln of lines) {
    if (/^#{2,3}\s/.test(ln)) { if (cur) blocks.push(cur); cur = { h: ln.trim(), body: [] }; }
    else if (cur) cur.body.push(ln);
  }
  if (cur) blocks.push(cur);
  for (const b of blocks) {
    const raw = b.h + '\n' + b.body.join('\n');
    if (raw.trim().length < 40) continue;
    const c = stripCode(raw);
    counts.total++;
    const claim = CLAIM.test(c), num = NUMBER.test(c);
    const selfStrong = SELF_STRONG.test(c), selfWeak = SELF_WEAK.test(c), src = SOURCE.test(c);
    let verdict;
    if (claim && num) {
      if (selfStrong) { verdict = 'selftested'; counts.selftested++; }
      else if (src || selfWeak) { verdict = 'secondhand'; counts.secondhand++; }
      else { verdict = 'faith'; counts.faith++; }
    } else if (claim && !num) { verdict = 'claimNoMetric'; counts.claimNoMetric++; }
    else { verdict = 'behavior'; counts.behavior++; }
    if (verdict !== 'behavior') rows.push({ file: rel, block: b.h.replace(/^#+\s/, '').slice(0, 60), verdict });
  }
}

const t = counts.total;
const summary = {
  total: t,
  behavior_NA: counts.behavior, behaviorPct: +(counts.behavior / t * 100).toFixed(0),
  secondhand_needsRepro: counts.secondhand,
  selftested_partial: counts.selftested,
  faith_unmeasured: counts.faith,
  claimNoMetric: counts.claimNoMetric,
};
// Of the blocks that actually make a metric/effect claim, how many are self-measured?
const metricClaims = counts.secondhand + counts.selftested + counts.faith + counts.claimNoMetric;
summary.effect_claims = metricClaims;
summary.effect_claims_selftested = counts.selftested;
summary.effect_claims_unproven = metricClaims - counts.selftested;
summary.effect_claims_unprovenPct = metricClaims ? +(summary.effect_claims_unproven / metricClaims * 100).toFixed(0) : 0;

const gate = { errors: 0, warnings: counts.faith > 0 ? 1 : 0, info: (counts.secondhand > 0 ? 1 : 0) + (counts.selftested > 0 ? 1 : 0) };
console.log(JSON.stringify({ corpus: corpusRoot, summary, gate, claimedRules: rows }, null, 2));
