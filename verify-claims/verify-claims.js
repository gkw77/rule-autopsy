#!/usr/bin/env node
// verify-claims — one command that re-runs every claim in this repo and prints a report.
//
//   Usage:
//     node verify-claims.js [corpus-root]
//       corpus-root  Rules directory to audit (recursive .md). Defaults to ../fixtures/rules.
//
//     node verify-claims.js --self-corpus <dir>
//       Audit your OWN rules directory instead. Run locally; never commit the result
//       if your rules contain private material — commit only the aggregate numbers.
//
// What it runs, in order:
//   1. rule-quality-audit.js   — block counts: verify signals / evidence / prose / placeholders
//   2. rule-evidence-audit.js  — claim×receipt verdicts on every effect-claiming block
//   3. receipts/gzh-rig        — dual-gate (source+product) lint capture, deterministic
//   4. receipts/agent-chief-rig— worthiness-gate metrics replay, deterministic (offline)
//
// Output: a sectioned, machine + human readable report. Deterministic when the corpus is fixed.

const { spawnSync } = require('child_process');
const fs = require('fs'), path = require('path');

const here = __dirname;
const repo = path.join(here, '..');
const fixture = path.join(repo, 'fixtures', 'rules');

let corpus = fixture;
if (process.argv.includes('--self-corpus')) {
  const i = process.argv.indexOf('--self-corpus');
  corpus = path.resolve(process.argv[i + 1]);
} else if (process.argv[2] && !process.argv[2].startsWith('-')) {
  corpus = path.resolve(process.argv[2]);
}

const py = process.platform === 'win32' ? 'python' : 'python3';

function runNode(script, args) {
  return spawnSync(process.execPath, [path.join(here, script), ...args], { encoding: 'utf8' });
}
function runPy(cwd, script) {
  return spawnSync(py, [script], { cwd, encoding: 'utf8', env: { ...process.env, PYTHONIOENCODING: 'utf-8' } });
}
function ok(r) { return r.status === 0; }
function firstLine(r) { return r.stdout.trim().split('\n')[0]; }

const report = [];
report.push(`# verify-claims report`);
report.push('');
report.push(`corpus: ${corpus}  (${fs.existsSync(corpus) ? 'exists' : 'MISSING'})`);
report.push(`date:   ${new Date().toISOString().slice(0, 10)}`);
report.push('');

// 1. quality audit
report.push('## 1. rule-quality-audit');
const q = runNode('rule-quality-audit.js', [corpus]);
if (ok(q)) {
  try {
    const j = JSON.parse(q.stdout);
    const s = j.summary;
    report.push(`- blocks ${s.blocks} | withVerify ${s.withVerify} (${s.withVerifyPct}%) | withEvidence ${s.withEvidence} (${s.withEvidencePct}%) | proseOnly ${s.proseOnly} (${s.proseOnlyPct}%) | placeholder ${s.placeholder} | vague ${s.vague}`);
  } catch { report.push(`- (parse error)\n${q.stdout.slice(0, 400)}`); }
} else {
  report.push(`- FAILED: ${q.stderr.slice(0, 400)}`);
}
report.push('');

// 2. evidence audit
report.push('## 2. rule-evidence-audit');
const e = runNode('rule-evidence-audit.js', [corpus]);
if (ok(e)) {
  try {
    const j = JSON.parse(e.stdout);
    const s = j.summary;
    report.push(`- blocks ${s.total} | behavior(NA) ${s.behavior_NA} (${s.behaviorPct}%)`);
    report.push(`- effect-claiming blocks: ${s.effect_claims}`);
    report.push(`-   selftested  ${s.selftested_partial}`);
    report.push(`-   secondhand  ${s.secondhand_needsRepro}`);
    report.push(`-   faith       ${s.faith_unmeasured}`);
    report.push(`-   claimNoMetric ${s.claimNoMetric}`);
    report.push(`- **unproven effect claims: ${s.effect_claims_unproven}/${s.effect_claims} (${s.effect_claims_unprovenPct}%)**`);
    if (s.effect_claims && j.claimedRules && j.claimedRules.length) {
      report.push('');
      report.push('claimed rule blocks:');
      for (const r of j.claimedRules) report.push(`- [${r.verdict}] ${r.file}: ${r.block}`);
    }
  } catch { report.push(`- (parse error)\n${e.stdout.slice(0, 400)}`); }
} else {
  report.push(`- FAILED: ${e.stderr.slice(0, 400)}`);
}
report.push('');

// 3. gzh dual-gate receipt (deterministic reproduction)
report.push('## 3. receipt: gzh dual-gate (reproduce)');
const g = runPy(path.join(repo, 'receipts', 'gzh-rig'), 'rig.py');
if (ok(g)) {
  try {
    const j = JSON.parse(g.stdout);
    const s = j.summary || {};
    report.push(`- defects ${s.defects} | source-only ${s.source_only_gate_capture} | product-only ${s.product_only_gate_capture} | double-gate ${s.double_gate_capture} | delta ${s.double_over_best_single_delta} | expectation mismatches ${s.expectation_mismatches}`);
    report.push(`- REPRODUCED ✓ (exit 0)`);
  } catch { report.push(`- ran (exit 0), output not JSON:\n${g.stdout.slice(0, 300)}`); }
} else {
  report.push(`- FAILED: ${g.stderr.slice(0, 400)}`);
}
report.push('');

// 4. agent-chief worthiness-gate metrics (deterministic offline replay)
report.push('## 4. receipt: agent-chief worthiness-gate metrics (reproduce)');
const a = runPy(path.join(repo, 'receipts', 'agent-chief-rig'), 'scripts/readme_metrics.py');
if (ok(a)) {
  const lines = a.stdout.replace(/\r/g, '').trim().split('\n').filter(Boolean).slice(0, 6).join(' | ');
  report.push(`- ${lines}`);
  report.push(`- REPRODUCED ✓ (exit 0)`);
} else {
  report.push(`- FAILED: ${a.stderr.slice(0, 400)}`);
}

report.push('');
report.push('Note: dao-cache (N=10, 95.9% vs 0%) needs a live ARK/Anthropic key; mcp-audit and post-verify-edit need a local ~/.claude session dir. They are documented in receipts/, not auto-run here.');

const out = report.join('\n');
console.log(out);
