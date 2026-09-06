#!/usr/bin/env python
# mcp-audit-rig.py - A4 P0-3 receipt rig for 03-routing "MCP 工具数量审计 -> 动态遥测"
# 测规则的前提命题：可用性(available) ≠ 调用(called)，静态 schema 计数高估真实负载，可量化浪费。
# 确定性、纯本地、无需 API key（与 gzh-rig 同档，N=1 有效无采样方差）。
# 咬合：03 MCP审计动态化(codex-hygiene) / 06 结构化门 / A4 度量门 / 02 token-diet
import os, json, glob, collections, sys
try:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows console 干净输出
except Exception:
    pass

HOME = os.path.expanduser("~")
PROJECTS = os.path.join(HOME, ".claude", "projects")
CLAUDE_JSON = os.path.join(HOME, ".claude.json")
SCHEMA_TOK_PER_TOOL = 500  # 03-routing 表：每工具 schema ≈ 500 tok

def split_mcp(name):
    # mcp__<server>__<tool> -> (server, tool) ; 内置工具 -> (None, name)
    if name.startswith("mcp__"):
        rest = name[5:]
        parts = rest.split("__", 1)
        if len(parts) == 2:
            return parts[0], parts[1]
    return None, name

def iter_tool_uses(files):
    """yield tool name for every tool_use block; stream line-by-line, never hold content"""
    for f in files:
        try:
            with open(f, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line or '"tool_use"' not in line:
                        continue
                    try:
                        obj = json.loads(line)
                    except Exception:
                        continue
                    msg = obj.get("message")
                    if not isinstance(msg, dict):
                        continue
                    content = msg.get("content")
                    if not isinstance(content, list):
                        continue
                    for blk in content:
                        if isinstance(blk, dict) and blk.get("type") == "tool_use" and "name" in blk:
                            yield blk["name"]
        except Exception:
            continue

def find_available_tools(files):
    """best-effort: scan jsonl for a 'tools':[{'name':...}] list (the loaded tool set).
    returns set() if not found."""
    found = set()
    for f in files:
        try:
            with open(f, encoding="utf-8") as fh:
                for line in fh:
                    if '"tools"' not in line:
                        continue
                    try:
                        obj = json.loads(line)
                    except Exception:
                        continue
                    # recurse for any 'tools' list of {name}
                    stack = [obj]
                    while stack:
                        cur = stack.pop()
                        if isinstance(cur, dict):
                            for k, v in cur.items():
                                if k == "tools" and isinstance(v, list):
                                    for t in v:
                                        if isinstance(t, dict) and "name" in t:
                                            found.add(t["name"])
                                else:
                                    stack.append(v)
                        elif isinstance(cur, list):
                            stack.extend(cur)
                    if found:
                        return found  # one good source is enough
        except Exception:
            continue
    return found

def configured_servers():
    """union of MCP server names from ~/.claude.json (top-level + per-project mcpServers) + .mcp.json"""
    servers = set()
    # ~/.claude.json
    try:
        with open(CLAUDE_JSON, encoding="utf-8") as fh:
            data = json.load(fh)
        top = data.get("mcpServers")
        if isinstance(top, dict):
            servers.update(top.keys())
        proj = data.get("projects")
        if isinstance(proj, dict):
            for p, cfg in proj.items():
                if isinstance(cfg, dict) and isinstance(cfg.get("mcpServers"), dict):
                    servers.update(cfg["mcpServers"].keys())
    except Exception:
        pass
    # project .mcp.json files
    for mj in glob.glob(os.path.join(PROJECTS, "**", ".mcp.json"), recursive=True):
        try:
            with open(mj, encoding="utf-8") as fh:
                d = json.load(fh)
            if isinstance(d.get("mcpServers"), dict):
                servers.update(d["mcpServers"].keys())
        except Exception:
            pass
    return servers

def main():
    files = glob.glob(os.path.join(PROJECTS, "**", "*.jsonl"), recursive=True)
    n_sessions = len(files)
    if not files:
        print("no session jsonl found under", PROJECTS)
        sys.exit(2)

    tool_calls = collections.Counter()
    server_calls = collections.Counter()
    n_calls = 0
    for name in iter_tool_uses(files):
        tool_calls[name] += 1
        srv, _ = split_mcp(name)
        if srv:
            server_calls[srv] += 1
        n_calls += 1

    called_tools = set(tool_calls)
    called_mcp_tools = {n for n in called_tools if n.startswith("mcp__")}
    called_servers = {split_mcp(n)[0] for n in called_mcp_tools}

    # available side
    avail_tools = find_available_tools(files)
    conf_servers = configured_servers()

    # server-level available != called
    never_called_servers = conf_servers - called_servers
    # tool-level (only if we found an available tool list)
    never_called_tools = (avail_tools - called_tools) if avail_tools else set()

    # Pareto on called tools
    ordered = sorted(tool_calls.values(), reverse=True)
    total = sum(ordered) or 1
    top20pct_n = max(1, len(ordered) // 5)
    top20pct_share = sum(ordered[:top20pct_n]) / total

    # schema-token tax (03 table: 500 tok/tool, per round)
    avail_for_tax = len(avail_tools) if avail_tools else None
    called_tax = len(called_tools) * SCHEMA_TOK_PER_TOOL
    if avail_for_tax is not None:
        static_tax = avail_for_tax * SCHEMA_TOK_PER_TOOL
        waste_per_round = len(never_called_tools) * SCHEMA_TOK_PER_TOOL
        overestimate_ratio = static_tax / called_tax if called_tax else None
    else:
        static_tax = None
        waste_per_round = None
        overestimate_ratio = None

    # GATE: 规则前提(available!=called / 静态高估 / 可量化浪费) 成立?
    confirmed = []
    if never_called_servers:
        confirmed.append(f"server-level: {len(never_called_servers)} configured-but-never-called server(s): {sorted(never_called_servers)}")
    if never_called_tools:
        confirmed.append(f"tool-level: {len(never_called_tools)} available-but-never-called tool(s)")
    if overestimate_ratio is not None and overestimate_ratio > 1.0:
        confirmed.append(f"static overestimates: {overestimate_ratio:.2f}x (static_tax={static_tax} vs called_tax={called_tax} tok/round)")
    if top20pct_share >= 0.80:
        confirmed.append(f"Pareto: top 20% tools ({top20pct_n}/{len(ordered)}) = {top20pct_share:.0%} of calls (tail = rare/waste candidate)")

    gate_pass = len(confirmed) > 0

    # 06 结构化门 JSON
    findings = []
    for s in sorted(never_called_servers):
        findings.append({"severity": "warning", "path": f"mcp:{s}", "message": "configured MCP server never invoked across all sessions (pure schema-token tax)"})
    if never_called_tools:
        findings.append({"severity": "info", "path": "mcp:tools", "message": f"{len(never_called_tools)} available tools never called; waste ≈ {waste_per_round} tok/round"})
    summary = {
        "sessions_scanned": n_sessions,
        "total_tool_calls": n_calls,
        "called_unique_tools": len(called_tools),
        "called_mcp_tools": len(called_mcp_tools),
        "called_mcp_servers": len(called_servers),
        "configured_servers": len(conf_servers),
        "never_called_servers": len(never_called_servers),
        "available_tools_known": avail_for_tax,
        "never_called_tools": len(never_called_tools),
        "static_tax_tok_per_round": static_tax,
        "called_tax_tok_per_round": called_tax,
        "waste_tok_per_round": waste_per_round,
        "overestimate_ratio": round(overestimate_ratio, 2) if overestimate_ratio else None,
        "pareto_top20pct_share": round(top20pct_share, 3),
        "gate_pass": gate_pass,
    }
    out = {"findings": findings, "summary": summary}

    print("=== MCP audit rig (03 P0-3, available vs called) ===")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    print("\n=== CONFIRMED claims ===")
    for c in confirmed:
        print("  +", c)
    if not confirmed:
        print("  (none)")
    print(f"\nGATE: {'PASS - 规则前提成立(available!=called, 静态高估, 可量化浪费)' if gate_pass else 'FAIL/NEEDS-REVIEW - 未观察到 available!=called 证据'}")

    # top called tools (transparency, no secrets - just names+counts)
    print("\n=== top 15 called tools ===")
    for name, c in tool_calls.most_common(15):
        print(f"  {c:>5}  {name}")

if __name__ == "__main__":
    main()
