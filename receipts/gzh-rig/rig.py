#!/usr/bin/env python3
"""gzh 双关卡 P0 rig (A4 度量)。
测 A2 声称："双关卡(源+产物) > 单关卡"。gzh 自带 validate_gzh_html.py(产物关卡)
+ component_lint.py(源关卡)，纯 stdlib 确定性 regex -> single-shot 有效(无采样方差)。

方法：种 19 个 HTML 缺陷，各标 source-only/product-only/both，跑 源单/产物单/双关卡，
数捕获率。双关卡 = 至少一道抓到。期望 both 严格优于任一单关卡。
诚实限制：确定性 lint，N=1 有效；但测的是"结构支配性"(union ⊃ each)，非真实文章逃逸率
(后者需真实生成文章分布)。
"""
import os, sys, json
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from validate_gzh_html import validate          # 产物关卡
from component_lint import lint_file            # 源关卡（读 .md 的 ```html 块）

RIG_DIR = os.path.dirname(os.path.abspath(__file__))
REFS = os.path.join(RIG_DIR, "references")
os.makedirs(REFS, exist_ok=True)

# (id, html, expect_src, src_sig, expect_prod, prod_sig, category)
DEFECTS = [
    ("style",      "<style>.x{color:red}</style>",            True,  "<style>",            True,  "<style> 标签会被过滤", "both"),
    ("script",     "<script>alert(1)</script>",               False, None,                True,  "<script> 标签会被过滤","product-only"),
    ("div",        "<div>x</div>",                            True,  "<div>",              True,  "<div> 会被改写",      "both"),
    ("link",       '<link rel="x" href="y.css">',             False, None,                True,  "外部 <link>",          "product-only"),
    ("class",      '<p class="x">y</p>',                      True,  "class 属性",         True,  "class 属性会被剥离",  "both"),
    ("id",         '<p id="y">z</p>',                         True,  "id 属性",            True,  "id 属性会被剥离",     "both"),
    ("position",   '<p style="position:fixed">x</p>',         True,  "position fixed",     True,  "position fixed/absolute/sticky", "both"),
    ("float",      '<p style="float:left">x</p>',             False, None,                True,  "float 不被支持",      "product-only"),
    ("media",      "@media(max-width:1px){}",                 True,  "@media",             True,  "@media 媒体查询",     "both"),
    ("keyframes",  "@keyframes x{from{}to{}}",                True,  "@media/@keyframes/@import", True, "@keyframes 动画", "both"),
    ("import",     "@import url(x.css);",                     True,  "@media/@keyframes/@import", True, "@import 不被支持","both"),
    ("grid",       '<p style="display:grid">x</p>',           True,  "display:grid",       True,  "display:grid 不被支持","both"),
    ("var",        '<p style="color:var(--c)">x</p>',         True,  "var(--x)",           True,  "CSS 变量",            "both"),
    ("fonturl",    "@font-face{src:url(https://x.com/f.woff)}",False,None,                 True,  "外部字体",            "product-only"),
    ("spanleaf",   "<p>中文内容</p>",                          False, None,                True,  "没有任何 <span leaf", "product-only"),
    ("halfpunct",  '<span leaf="">中文,内容</span>',           False, None,                True,  "半角标点",            "product-only"),
    ("asciiquote", '<span leaf="">他说"好"</span>',            False, None,                True,  "半角标点",            "product-only"),
    ("whitespace", '<p style="white-space:pre">x</p>',        True,  "white-space:pre",    False, None,                  "source-only"),
    ("dashed",     '<section style="border:1px dashed red">x</section>', True, "四周虚线框", False, None,              "source-only"),
]

def run_source(html):
    """把 html 包进 .md 的 ```html 块，调 lint_file。返回 (caught, msgs, n_err, n_warn)。"""
    path = os.path.join(REFS, "_rig_probe.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("# probe\n```html\n" + html + "\n```\n")
    _, found = lint_file(path)
    msgs = [m for _, m in found]
    n_err = sum(1 for lv, _ in found if lv == "ERROR")
    n_warn = sum(1 for lv, _ in found if lv == "WARN")
    return msgs, n_err, n_warn

def run_product(html):
    errs, warns, _ = validate(html, "<rig>")
    msgs = errs + warns
    return msgs, len(errs), len(warns)

rows = []
src_caught = prod_caught = both_caught = 0
mismatch = 0
for did, html, exp_s, sig_s, exp_p, sig_p, cat in DEFECTS:
    s_msgs, s_e, s_w = run_source(html)
    p_msgs, p_e, p_w = run_product(html)
    act_s = any(sig_s in m for m in s_msgs) if sig_s else False
    act_p = any(sig_p in m for m in p_msgs) if sig_p else False
    # 诚实：expect=False 时也报 raw 计数，便于发现误抓
    ok = (act_s == exp_s) and (act_p == exp_p)
    if not ok: mismatch += 1
    if act_s: src_caught += 1
    if act_p: prod_caught += 1
    if act_s or act_p: both_caught += 1
    rows.append({
        "defect": did, "category": cat,
        "src": {"expect": exp_s, "actual": act_s, "errs": s_e, "warns": s_w},
        "prod":{"expect": exp_p, "actual": act_p, "errs": p_e, "warns": p_w},
        "match": ok,
    })

n = len(DEFECTS)
summary = {
    "defects": n,
    "source_only_gate_capture": f"{src_caught}/{n} ({round(src_caught/n*100)}%)",
    "product_only_gate_capture": f"{prod_caught}/{n} ({round(prod_caught/n*100)}%)",
    "double_gate_capture": f"{both_caught}/{n} ({round(both_caught/n*100)}%)",
    "double_over_best_single_delta": f"+{both_caught - max(src_caught,prod_caught)}/{n} ({round((both_caught-max(src_caught,prod_caught))/n*100)}%)",
    "expectation_mismatches": mismatch,
    "rig_validity": "deterministic regex lint, N=1 valid (no sampling variance)",
    "honest_limit": "tests structural dominance (union ⊃ each), not real-article escape rate (needs real generated-article distribution)",
}
gate = {"errors": mismatch, "warnings": 0, "info": 1 if both_caught <= max(src_caught,prod_caught) else 0}
print(json.dumps({"summary": summary, "gate": gate, "rows": rows}, ensure_ascii=False, indent=2))
