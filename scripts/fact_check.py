#!/usr/bin/env python3
"""fact_check.py — 源文/译文事实层对账（只报候选差异，不裁决）。

用法: python3 fact_check.py <源文> <译文> [--context 15]
抽取两边的数字（含货币符号、大数单位、百分比）、日期、URL、邮箱、占位符，
按归一化后的核心值比较，列出"只在源文"与"只在译文"的候选差异。
stdlib only.
"""
import re
import sys
import unicodedata
from collections import Counter

CURRENCY = r"[¥￥$€£]|USD|CNY|JPY|RMB|EUR|GBP|US\$|NT\$|HK\$"
BIG_UNIT = r"(?:万亿|万|亿|億|兆|千|百|百万|K|M|B|T)?"
NUM_CORE = r"\d+(?:[,，]\d{3})*(?:[.．]\d+)?"

RE_NUMBER = re.compile(
    rf"(?P<cur>(?:{CURRENCY})\s?)?(?P<num>{NUM_CORE})\s?(?P<unit>{BIG_UNIT})(?P<pct>\s?[%％])?(?P<cur2>\s?(?:元|円|ドル|美元|日元|人民元|人民币))?"
)
RE_DATE = re.compile(
    r"(?:令和|平成|昭和|民國|民国)\s?\d{1,3}\s?年(?:\s?\d{1,2}\s?月(?:\s?\d{1,2}\s?日)?)?"
    r"|\d{4}\s?[-/.年]\s?\d{1,2}(?:\s?[-/.月]\s?\d{1,2}\s?日?)?"
    r"|\d{1,2}/\d{1,2}/\d{2,4}"
    r"|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}"
    r"|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}"
)
RE_URL = re.compile(r"https?://[^\s<>\"'）)】\]]+|www\.[^\s<>\"'）)】\]]+|\b[a-z0-9-]+\.(?:ai|com|io|jp|cn|net|org|co)(?:/[^\s<>\"'）)】\]]*)?")
RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
RE_PLACEHOLDER = re.compile(r"\{[^{}]*\}|%\d*\$?[sdif]|\$\{[^}]*\}|\{\{[^}]*\}\}")
RE_CURRENCY_SYM = re.compile(r"[¥￥$€£]")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def nfkc(s):
    return unicodedata.normalize("NFKC", s)


def snippet(text, start, end, ctx):
    a = max(0, start - ctx)
    b = min(len(text), end + ctx)
    return text[a:b].replace("\n", " ")


def extract_numbers(text, ctx):
    out = []
    for m in RE_NUMBER.finditer(text):
        raw = m.group(0)
        core = nfkc(m.group("num")).replace(",", "")
        unit = m.group("unit") or ""
        pct = "%" if m.group("pct") else ""
        cur = (m.group("cur") or "").strip() or (m.group("cur2") or "").strip()
        key = f"{core}{unit}{pct}"
        out.append({"key": key, "raw": raw.strip(), "cur": cur, "ctx": snippet(text, m.start(), m.end(), ctx)})
    return out


def extract(regex, text, ctx):
    return [{"key": re.sub(r"\s+", "", nfkc(m.group(0))), "raw": m.group(0), "ctx": snippet(text, m.start(), m.end(), ctx)} for m in regex.finditer(text)]


def diff(src_items, tgt_items):
    sc = Counter(i["key"] for i in src_items)
    tc = Counter(i["key"] for i in tgt_items)
    only_src = sc - tc
    only_tgt = tc - sc
    return only_src, only_tgt


def first_ctx(items, key):
    for i in items:
        if i["key"] == key:
            return i["ctx"]
    return ""


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source"); ap.add_argument("target")
    ap.add_argument("--context", type=int, default=15)
    a = ap.parse_args()
    args, ctx = [a.source, a.target], a.context
    src, tgt = read(args[0]), read(args[1])

    print("# fact_check 报告\n")
    print(f"源文: {args[0]}  ({len(src)} 字符)\n译文: {args[1]}  ({len(tgt)} 字符)\n")
    print("说明：只列候选差异；等值换算（1.2亿 vs 1億2,000万）、币种标注变化需要人判断。涉及符号和单位的地方必须回源文确认。\n")

    total = 0
    # numbers
    sn, tn = extract_numbers(src, ctx), extract_numbers(tgt, ctx)
    os_, ot = diff(sn, tn)
    print(f"## 1. 数字（源 {len(sn)} 个 / 译 {len(tn)} 个）")
    if not os_ and not ot:
        print("- 核心值集合一致。")
    for k, n in os_.items():
        total += 1
        print(f"- 只在源文 ×{n}: `{k}`  … {first_ctx(sn, k)}")
    for k, n in ot.items():
        total += 1
        print(f"- 只在译文 ×{n}: `{k}`  … {first_ctx(tn, k)}")

    # currency symbols
    print("\n## 2. 货币符号计数（符号在不同 locale 指向不同货币，必须回源文确认指什么）")
    cs, ct = Counter(RE_CURRENCY_SYM.findall(src)), Counter(RE_CURRENCY_SYM.findall(tgt))
    for sym in sorted(set(cs) | set(ct)):
        flag = "  ← 译文原样保留了源文符号，确认币种" if cs.get(sym) and ct.get(sym) and sym in "¥￥" else ""
        print(f"- `{sym}`: 源 {cs.get(sym, 0)} / 译 {ct.get(sym, 0)}{flag}")
    if not cs and not ct:
        print("- 无货币符号。")
    # words for currency
    for w in ["元", "円", "日元", "人民币", "人民元", "ドル", "美元", "USD", "CNY", "JPY", "RMB"]:
        a, b = src.count(w), tgt.count(w)
        if a or b:
            print(f"- 「{w}」: 源 {a} / 译 {b}")

    # dates
    sd, td = extract(RE_DATE, src, ctx), extract(RE_DATE, tgt, ctx)
    os_, ot = diff(sd, td)
    print(f"\n## 3. 日期（源 {len(sd)} / 译 {len(td)}）")
    if not os_ and not ot:
        print("- 字面一致（格式不同但同一天的，人工确认）。" if sd or td else "- 无日期。")
    for k, n in os_.items():
        total += 1
        print(f"- 只在源文 ×{n}: `{k}`  … {first_ctx(sd, k)}")
    for k, n in ot.items():
        total += 1
        print(f"- 只在译文 ×{n}: `{k}`  … {first_ctx(td, k)}")

    # urls & emails
    for title, rx in (("4. URL", RE_URL), ("5. 邮箱", RE_EMAIL)):
        s_, t_ = extract(rx, src, ctx), extract(rx, tgt, ctx)
        os_, ot = diff(s_, t_)
        print(f"\n## {title}（源 {len(s_)} / 译 {len(t_)}）")
        if not os_ and not ot:
            print("- 一致。" if s_ or t_ else "- 无。")
        for k, n in os_.items():
            total += 1
            print(f"- 只在源文 ×{n}: `{k}`")
        for k, n in ot.items():
            total += 1
            print(f"- 只在译文 ×{n}: `{k}`  ← 译文擅自加的路径/链接？确认真实存在")

    # placeholders
    sp, tp = extract(RE_PLACEHOLDER, src, ctx), extract(RE_PLACEHOLDER, tgt, ctx)
    os_, ot = diff(sp, tp)
    print(f"\n## 6. 占位符/变量（源 {len(sp)} / 译 {len(tp)}）")
    if not os_ and not ot:
        print("- 一致。" if sp or tp else "- 无。")
    for k, n in os_.items():
        total += 1
        print(f"- 只在源文 ×{n}: `{k}`")
    for k, n in ot.items():
        total += 1
        print(f"- 只在译文 ×{n}: `{k}`")

    print(f"\n## 汇总\n- 候选差异: {total} 项")


if __name__ == "__main__":
    main()
