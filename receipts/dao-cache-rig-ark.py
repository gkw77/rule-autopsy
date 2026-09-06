#!/usr/bin/env python3
"""dao-code cache-stability rig - ARK 适配版（2026-07-14）。

测 02-context 缓存稳定段 claim："前缀字节稳定 -> 高 prompt-cache-hit"（dao-code 报 95.8%）。
A arm 稳定前缀 vs B arm 前缀漂移（volatile 注入**前缀**破前缀字节稳定），N=10 取 median。

vs 原 dao-cache-rig.py 的两处修：
  1. 适配 ARK coding 端点（ANTHROPIC_AUTH_TOKEN + ANTHROPIC_BASE_URL + urllib，不依赖官方 SDK/ANTHROPIC_API_KEY）
  2. **修 drift bug**：原版 drift=STABLE+尾部volatile，但 Anthropic 缓存是前缀匹配，尾部 volatile 不破前缀 -> drift 仍命中 -> 假 FAIL。
     本版 drift=volatile前缀+STABLE，真破前缀字节稳定。
  3. STABLE 加大到 *220（~1300 tokens）过 glm-5.2 缓存门槛（探测确认 *220 能命中）。

复现：python dao-cache-rig-ark.py   (在此目录运行; 可设 RIG_N, 默认 10)
诚实限制：glm-5.2 是 thinking 模型，max_tokens 留 1024 防 thinking 截断；ARK usage 不报 cache_creation（只报 cache_read），hit_rate=read/(read+input)。
"""
import os, json, urllib.request, ssl, time, statistics

TOKEN = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
BASE = os.environ.get("ANTHROPIC_BASE_URL", "https://ark.cn-beijing.volces.com/api/coding")
MODEL = os.environ.get("ANTHROPIC_MODEL", "glm-5.2")
N = int(os.environ.get("RIG_N", "10"))

STABLE = "You are a coding assistant. " * 220  # ~1300 tokens, >glm-5.2 缓存门槛

def drift(i):
    # volatile 注入**前缀**（修原 rig 的尾部 bug）--破前缀字节稳定 -> 缓存不命中
    return f"[turn {i} {time.time()}]\n" + STABLE

_ctx = ssl.create_default_context(); _ctx.check_hostname = False; _ctx.verify_mode = ssl.CERT_NONE

def call(sys_text):
    body = {"model": MODEL, "max_tokens": 1024,
            "system": [{"type": "text", "text": sys_text, "cache_control": {"type": "ephemeral"}}],
            "messages": [{"role": "user", "content": "reply OK"}]}
    req = urllib.request.Request(BASE + "/v1/messages", data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {TOKEN}", "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, context=_ctx, timeout=120) as r:
        return json.load(r)

def arm(sys_fn):
    hits = []
    for i in range(N):
        sys_text = sys_fn(i) if callable(sys_fn) else sys_fn
        u = call(sys_text).get("usage", {})
        read = u.get("cache_read_input_tokens", 0) or 0
        inp = u.get("input_tokens", 0) or 0
        tot = read + inp
        hits.append(read / tot if tot else 0)
        time.sleep(0.5)
    return statistics.median(hits), hits

if __name__ == "__main__":
    if not TOKEN:
        print("缺 ANTHROPIC_AUTH_TOKEN"); raise SystemExit(1)
    print(f"ARK dao-cache rig: model={MODEL} base={BASE} N={N}")
    a_med, a_all = arm(lambda i: STABLE)
    print(f"A stable-prefix : median={a_med:.1%}  all={[f'{x:.0%}' for x in a_all]}")
    b_med, b_all = arm(drift)
    print(f"B drift-prefix  : median={b_med:.1%}  all={[f'{x:.0%}' for x in b_all]}")
    delta = a_med - b_med
    print(f"delta: +{delta:.1%}  (正=稳定前缀 cache-hit 更高，验证 dao-code claim)")
    gate = a_med > b_med and delta > 0.30
    print(f"GATE: {'PASS' if gate else 'FAIL/NEEDS-REVIEW'}  (A>B 且 delta>30%)")
