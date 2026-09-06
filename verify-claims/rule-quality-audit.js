#!/usr/bin/env node
// rule-quality-audit.js — structured audit of rule-file quality (A4/04/A1 applied to yourself).
//
//   Usage:  node rule-quality-audit.js [corpus-root]
//
//   corpus-root  Directory of markdown rules to audit (walked recursively).
//                Defaults to ../fixtures/rules (a small public demo corpus).
//
// What it counts, per markdown block (split at ## / ### headings):
//   blocks        total blocks
//   withVerify    blocks carrying a machine-checkable verify signal
//   withEvidence  blocks citing any measured evidence
//   withSource    blocks citing an external source
//   proseOnly     blocks with neither a verify signal nor evidence
//   placeholder   blocks with TBD / "add appropriate error handling" style cop-outs
//   vague         blocks with hedge language
//
// Code blocks and inline code are stripped first so quoted anti-patterns don't
// trip the detectors. Output is 06-style structured JSON (machine-consumable).

const fs = require('fs'), path = require('path');
const corpusRoot = path.resolve(process.argv[2] || path.join(__dirname, '..', 'fixtures', 'rules'));

const PLACEHOLDER = /TBD|implement later|fill in details|add appropriate|add validation|handle edge cases|适当处理|稍后|待补/i;
const VAGUE = /usually|generally|roughly|probably|sort of|kind of|尽可能|尽量|适当|合理地/i;
const VERIFY_SIG = /Verify:|→ .*expect|machine-checkable|gate|errors\s*>\s*0|summary\.|stop condition|termination|verify-claims|validator|expected output/i;
const EVIDENCE = /measured|N runs|N≥|median|benchmark|data point|实测|\d+\s*runs|agentic/i;
const SOURCE = /(?:from|via|inspired by)\s+\S|来自\s+\S/i;

// Walk a directory tree for .md files.
function walk(dir, acc = []) {
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, ent.name);
    if (ent.isDirectory()) walk(p, acc);
    else if (ent.name.toLowerCase().endsWith('.md')) acc.push(p);
  }
  return acc;
}

// Strip fenced + inline code so quoted examples / anti-patterns don't false-positive.
function stripCode(t) { return t.replace(/```[\s\S]*?```/g, ' ').replace(/`[^`\n]*`/g, ' '); }

const findings = [];
const stats = { blocks: 0, withVerify: 0, withEvidence: 0, withSource: 0, placeholder: 0, vague: 0, proseOnly: 0 };

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
    const content = stripCode(raw);
    stats.blocks++;
    const hasV = VERIFY_SIG.test(content); if (hasV) stats.withVerify++;
    const hasE = EVIDENCE.test(content); if (hasE) stats.withEvidence++;
    const hasS = SOURCE.test(content); if (hasS) stats.withSource++;
    if (PLACEHOLDER.test(content)) { stats.placeholder++; findings.push({ file: rel, block: b.h, issue: 'placeholder / vague commitment', type: 'placeholder' }); }
    if (VAGUE.test(content)) { stats.vague++; findings.push({ file: rel, block: b.h, issue: 'hedge language', type: 'vague' }); }
    if (!hasV && !hasE) stats.proseOnly++;
  }
}

const summary = {
  blocks: stats.blocks,
  withVerify: stats.withVerify, withVerifyPct: +(stats.withVerify / stats.blocks * 100).toFixed(0),
  withEvidence: stats.withEvidence, withEvidencePct: +(stats.withEvidence / stats.blocks * 100).toFixed(0),
  withSource: stats.withSource,
  proseOnly: stats.proseOnly, proseOnlyPct: +(stats.proseOnly / stats.blocks * 100).toFixed(0),
  placeholder: stats.placeholder, vague: stats.vague,
};
const gate = { errors: 0, warnings: (stats.placeholder > 0 ? 1 : 0) + (stats.withEvidence / stats.blocks < 0.2 ? 1 : 0), info: 0 };
console.log(JSON.stringify({ corpus: corpusRoot, summary, gate, findings }, null, 2));
