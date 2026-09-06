#!/usr/bin/env python3
"""
post-verify-edit-rig.py  —  测量型 receipt #4（2026-07-14）
证 06 mindwalk「run 审查信号: edits-after-last-verify」的前提命题：
  该信号能否从本地 session jsonl 量化提取 + 本环境分布。

read-only：扫 ~/.claude/projects/**/*.jsonl，只聚合 tool 名+序列，不打印内容。

诚实限定：
  - verify 识别是启发式 regex（Bash 命令含 test/lint/build/pytest/tsc 等）-> 漏判+误判
  - "post-verify edit" ≠ "unverified-bug"（可能是正当收尾：注释/格式/文档）
    -> 完整 efficacy（post-verify edit 与 unverified-bug 相关性）需跨 session 人工标注，单对话不可行
  - 只计 Edit/Write/NotebookEdit/MultiEdit，漏 Bash 的 sed/echo> 等文件修改 -> 低估 edits
  - N=1 确定性统计（无采样方差），单用户非跨用户普适

复现：python post-verify-edit-rig.py  (在此目录运行; 扫本机 ~/.claude/projects)
"""
import os, json, glob, re, statistics
from collections import Counter

ROOT = os.path.expanduser("~/.claude/projects")
files = glob.glob(os.path.join(ROOT, "**", "*.jsonl"), recursive=True)

EDIT_TOOLS = {"Edit", "Write", "NotebookEdit", "MultiEdit"}
VERIFY_RE = re.compile(r"\b(pytest|unittest|jest|vitest|mocha|npm test|yarn test|pnpm test|cargo test|cargo check|go test|rustc|tsc|--type-check|lint|eslint|biome|ruff|flake8|pylint|mypy|bandit|build|make|cmake|--build|verify|conftest)\b", re.I)

def classify(tool_name, tool_input):
    if tool_name in EDIT_TOOLS:
        return "edit"
    if tool_name == "Bash":
        cmd = (tool_input.get("command") or "") if isinstance(tool_input, dict) else ""
        if VERIFY_RE.search(cmd):
            return "verify"
    if tool_name in ("Task", "Agent") and isinstance(tool_input, dict):
        desc = (tool_input.get("description") or "") + " " + (tool_input.get("prompt") or "")
        if re.search(r"\b(review|verify|test|audit|check|lint)\b", desc, re.I):
            return "verify"
    return "other"

total_sessions = sessions_with_verify = sessions_with_post_verify_edit = 0
post_verify_edit_counts = []
total_post_verify_edits = total_edits = zero_verify_but_edited = 0

for fp in files:
    seq = []
    try:
        with open(fp, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except Exception:
                    continue
                if ev.get("type") == "assistant":
                    for c in (ev.get("message", {}).get("content", []) or []):
                        if isinstance(c, dict) and c.get("type") == "tool_use":
                            seq.append(classify(c.get("name", ""), c.get("input", {}) or {}))
    except Exception:
        continue
    if not seq:
        continue
    total_sessions += 1
    edits = [i for i, t in enumerate(seq) if t == "edit"]
    verifies = [i for i, t in enumerate(seq) if t == "verify"]
    total_edits += len(edits)
    if not verifies:
        if edits:
            zero_verify_but_edited += 1
        continue
    sessions_with_verify += 1
    pe = sum(1 for i in edits if i > verifies[-1])
    total_post_verify_edits += pe
    post_verify_edit_counts.append(pe)
    if pe > 0:
        sessions_with_post_verify_edit += 1

n = len(post_verify_edit_counts)
print(f"jsonl files scanned: {len(files)}")
print(f"sessions with any tool seq: {total_sessions}")
print(f"  with >=1 verify call: {sessions_with_verify}")
print(f"  with edits but ZERO verify: {zero_verify_but_edited}  (no gate at all)")
print(f"total edit calls: {total_edits}")
print(f"total edits AFTER last verify: {total_post_verify_edits}")
print(f"sessions w/ post-verify edits: {sessions_with_post_verify_edit} / {sessions_with_verify} = "
      f"{100 * sessions_with_post_verify_edit / max(1, sessions_with_verify):.1f}%")
if n:
    srt = sorted(post_verify_edit_counts)
    print(f"post-verify-edits per verifying-session: median={statistics.median(srt)} max={srt[-1]} mean={statistics.mean(srt):.1f}")
    buckets = Counter(0 if x == 0 else (1 if x <= 2 else (3 if x <= 5 else 6)) for x in srt)
    print(f"  distribution: 0 edits={buckets[0]} | 1-2={buckets[1]} | 3-5={buckets[2]} | 6+={buckets[3]}")
print(f"\nUNVERIFIED-WORK RATIO (post-verify edits / all edits): "
      f"{100 * total_post_verify_edits / max(1, total_edits):.1f}%")
