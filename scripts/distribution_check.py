#!/usr/bin/env python3
"""distribution_check.py — 双语表的描述性分布统计，不判定翻译质量。

用法: python3 distribution_check.py <双语表.md> --src-col N --tgt-col N
                                   --target-locale ja [--source-locale en-US]
统计前排除常见 Markdown 语法；不是完整解析器，引用式链接等复杂结构需人工复核。
分布相似或相异均不能单独证明机械翻译，也不表示质量高低。
"""
import re
import sys
import argparse
from collections import Counter, defaultdict
import unicodedata
from markdown_utils import prose_view, table_rows

JA_POLITE = re.compile(r"(ます|ました|ません|ませんでした|です|でした|ください|下さい)[。！？]?$")
SEPS = "・：:／/、，,＋+—–-｜|　"


def rows_of(path, sc, tc):
    return [(n, c[sc], c[tc]) for n, c in table_rows(path)
            if len(c) > max(sc, tc) and (c[sc] or c[tc])]


def ja_register(t):
    """语体分类。只看可见文字的结尾，不做语法分析。"""
    s = re.sub(r"[（(].*?[)）]\s*$", "", prose_view(t)).strip()
    if not s:
        return "空"
    if JA_POLITE.search(s):
        return "です・ます"
    if s.endswith(("。", "！", "？")):
        return "常体/その他の文"
    if re.search(r"[ぁ-ん]$", s):
        return "用言止め（。なし）"
    return "体言止め"


def _language(locale):
    return locale.lower().replace('_', '-').split('-')[0]


def _sentence_view(text):
    text = prose_view(text)
    text = re.sub(r"\*\.[A-Za-z0-9]+", " ", text)
    text = re.sub(r"(?<=\d)\.(?=\d)", "", text)
    text = re.sub(r"(?<=\w)\.(?=[A-Za-z0-9])", "", text)
    return text


def sent_breaks(t, lang):
    pattern = r"[.!?]" if _language(lang) == "en" else r"[。．！？!?]"
    return len(re.findall(pattern, _sentence_view(t)))


_CURRENCY_WORD = r"USD|CNY|JPY|RMB|EUR|GBP|人民元|人民币|日元|米ドル|美元|ドル|dollars?|円|元"
_CURRENCY_PREFIX = rf"US\$|[¥￥$€£]|(?<!\w)(?:{_CURRENCY_WORD})"
_CURRENCY_SUFFIX = r"USD|CNY|JPY|RMB|EUR|GBP|人民元|人民币|日元|米ドル|美元|ドル|dollars?|円|元(?![一-鿿㐀-䶿])"
_AMOUNT = r"\d+(?:,\d{3})*(?:\.\d+)?\s*[万億亿兆千百KMBT]*"
_MONEY = re.compile(
    rf"(?P<before>{_CURRENCY_PREFIX})\s*{_AMOUNT}(?![A-Za-z])"
    rf"|(?<![\dA-Za-z]){_AMOUNT}\s*(?P<after>{_CURRENCY_SUFFIX})(?![A-Za-z])",
    re.I,
)
_CANONICAL = {"人民元": "CNY", "人民币": "CNY", "元": "CNY", "RMB": "CNY",
              "円": "JPY", "日元": "JPY", "米ドル": "USD", "美元": "USD",
              "ドル": "USD", "$": "USD", "US$": "USD", "DOLLAR": "USD",
              "DOLLARS": "USD", "¥": "¥(币种待确认)", "￥": "¥(币种待确认)",
              "€": "EUR", "£": "GBP"}


def _currency_tokens(text):
    found = Counter()
    for m in _MONEY.finditer(unicodedata.normalize("NFKC", prose_view(text))):
        raw = (m.group('before') or m.group('after')).upper()
        found[_CANONICAL.get(raw, raw)] += 1
    return found


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("file"); p.add_argument("--src-col", type=int, required=True)
    p.add_argument("--tgt-col", type=int, required=True)
    p.add_argument("--target-locale", required=True); p.add_argument("--source-locale", default="")
    a = p.parse_args()
    if min(a.src_col, a.tgt_col) < 0 or a.src_col == a.tgt_col:
        p.error("源译列须为不同的非负整数。")
    rows = rows_of(a.file, a.src_col, a.tgt_col)
    print(f"# distribution_check 报告\n\n文件 `{a.file}`（源文第 {a.src_col} 列 / 译文第 {a.tgt_col} 列）")
    if not rows:
        print("\n**解析出 0 行。这不等于通过——多半是列号指错了。**"); sys.exit(2)
    print(f"\n**回显前 2 行**，确认列号没指错：")
    for n, s, t in rows[:2]:
        print(f"- L{n}　源`{s[:26]}`　→　译`{t[:26]}`")
    print(f"\n解析 {len(rows)} 行。\n")

    prose_rows = [(n, prose_view(s), prose_view(t)) for n, s, t in rows]
    print("统计视图：排除表头、链接目标、行内代码和列表标记；保留可见文字及全角空格。不是完整 Markdown 渲染器。\n")

    # ── 1. 语体分布（ja） ─────────────────────────────
    if a.target_locale.startswith("ja"):
        reg = Counter(ja_register(t) for _, _, t in prose_rows if t)
        tot = sum(reg.values())
        print("## 1. 语体分布\n\n| 语体 | 条数 | 占比 |\n|---|---|---|")
        for k, v in reg.most_common():
            print(f"| {k} | {v} | {v/tot:.0%} |")
        # 转写率：源文有无句点 → 译文语体
        xt = defaultdict(Counter)
        for _, s, t in prose_rows:
            if not t:
                continue
            terminal = r"[.]\s*$" if _language(a.source_locale) == "en" else r"[。．]\s*$"
            xt["源文に句点あり" if re.search(terminal, s) else "源文に句点なし"][ja_register(t)] += 1
        print("\n### 依存度：源文有没有句点，能不能预测译文的语体\n")
        A, B = xt["源文に句点あり"], xt["源文に句点なし"]
        nA, nB = sum(A.values()), sum(B.values())
        if nA and nB:
            keys = sorted(set(A) | set(B))
            print("| 语体 | 源文に句点あり | 源文に句点なし | 差 |\n|---|---|---|---|")
            tvd = 0.0
            for k in keys:
                pa, pb = A[k] / nA, B[k] / nB
                tvd += abs(pa - pb)
                print(f"| {k} | {pa:.0%}（{A[k]}/{nA}） | {pb:.0%}（{B[k]}/{nB}） | {(pa-pb)*100:+.1f}pp |")
            tvd /= 2
            pol = (A["です・ます"] / nA - B["です・ます"] / nB) * 100
            print(f"\n**依存度（分布差 TVD）＝ {tvd:.2f}**　／　**です・ます の差 ＝ {pol:+.1f}pp**\n")
            print("数值只描述两组分布的差异，不能证明因果，也不是翻译质量分数；角色分布可能同时影响源译标点。\n")
            print("> **注意：不要用「各组的众数占比」当这个指标。** 那是本脚本第一版的错——\n"
                  "> 当译文**正确地统一到目标语惯例**时，两组的众数会收敛到同一个值，众数占比反而**升高**，\n"
                  "> 公式会把「改对了」记成「没改」。实测：某次修订依存度从 +91.7pp 降到 -0.6pp（正确），\n"
                  "> 而众数占比 92% → 92%（纹丝不动）。**要量的是两组分布之差，不是各组内部的集中度。**\n")
            print("日语幻灯片的惯例是**体言止め主体、です・ます 只用于需要说明的整句**——"
                  "依据应当是「这一格在版面上扮演什么角色」，**不是源文有没有句号**。")

    # ── 2. 句读点密度的转写 ────────────────────────────
    sb = [(sent_breaks(s, a.source_locale), sent_breaks(t, a.target_locale)) for _, s, t in rows]
    # 两边都是 0 的行要剔掉——短标签本来就没有句点，0==0 是白送的，会把比例灌到 99%
    live = [(x, y) for x, y in sb if x or y]
    same = sum(1 for x, y in live if x == y)
    trivial = len(sb) - len(live)
    print(f"\n## 2. 断句的转写\n")
    print(f"- 两边都无句点的行（短标签，不计入）：{trivial}/{len(sb)}")
    if live:
        print(f"- **有效行 {len(live)} 行中，源文与译文句读点个数完全相同：{same}（{same/len(live):.0%}）**\n")
        print("相同比例仅供审校定位，不是越低越好；相同断句也可能正确，差异也可能来自漏译。")
    else:
        print("- 有效行 0，本项不适用。\n")

    # ── 3. 分隔符的角色分工 ───────────────────────────
    print("\n## 3. 分隔符各自在干几份活\n")
    print("| 符号 | 出现 | 出现在的格子长度（em 中位） | 最短例 | 最长例 |\n|---|---|---|---|---|")
    W = lambda s: sum(1.0 if ord(ch) > 0x2E80 else 0.55 for ch in s)
    for ch in SEPS:
        hit = [plain for _, _, t in rows if (plain := prose_view(t)) and ch in plain]
        if len(hit) < 2:
            continue
        ws = sorted(W(x) for x in hit)
        med = ws[len(ws)//2]
        shortest = min(hit, key=W); longest = max(hit, key=W)
        name = "全角スペース" if ch == "　" else ch
        print(f"| `{name}` | {len(hit)} | {med:.0f} | `{shortest[:22]}` | `{longest[:30]}` |")
    print("\n上表为符号出现行数和上下文样例，不自动判定符号角色或错误；需结合材料体例复核。")

    # ── 4. 货币记法 ──────────────────────────────
    local = {"ja": "JPY", "ja-jp": "JPY", "zh-cn": "CNY",
             "en-us": "USD", "en-gb": "GBP"}.get(a.target_locale.lower().replace("_", "-"))
    src_cur = Counter()
    tgt_cur = Counter()
    local_rows = 0
    for _, s, t in rows:
        src_cur.update(_currency_tokens(s))
        currencies = _currency_tokens(t)
        tgt_cur.update(currencies)
        local_rows += bool(local and currencies.get(local))
    print(f"\n## 4. 货币记法\n\n带金额的源文币种候选：{dict(src_cur) or '无'}")
    print(f"带金额的译文币种候选：{dict(tgt_cur) or '无'}")
    print(f"含参考币种 {local or '地区未指定'} 的译文行：{local_rows}")
    print("币种仍需结合地区/上下文确认，尤其 ¥/$；缺少换算不自动判错。")
    if local and tgt_cur and not local_rows:
        print("待确认：金额只有外币或歧义符号；是否补充换算由材料场景及项目决定。")



if __name__ == "__main__":
    main()
