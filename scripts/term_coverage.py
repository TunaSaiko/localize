#!/usr/bin/env python3
"""term_coverage.py — 术语表覆盖率与执行一致性（只报告不裁决）。

用法:
  # ① 覆盖闸：源文里的高频实词，术语表收了没有
  python3 term_coverage.py cover <源文> --glossary <术语表.md> --src-lang zh|ja|en [--min 4] [--gloss-src-col 2]

  # ② 执行闸：术语表定了的词，译文里真的照用了吗
  python3 term_coverage.py enforce <双语表.md> --glossary <术语表.md> \
      --src-col 2 --tgt-col 3 --gloss-src-col 2 --gloss-tgt-col 3

**为什么要有这个脚本**（实测，某商业提案 zh→ja）：
  术语表**收录**的词，译文一致性 100%（两个核心术语分别 19/19、3/3）。
  不一致的全部是**表外词或只有复合词条目的词**：
    企业(10 处) 只有「企业○○」这种复合词条目 → 企業×2 / 法人×8
    团队(9 处)  完全表外                        → チーム×6 / 組織×3
  **失败的不是执行，是覆盖。** 而覆盖是数得出来的——所以交给脚本。

stdlib only。输出 markdown。
"""
import re
import sys
import argparse
from collections import Counter, defaultdict

CJK = r"[一-鿿㐀-䶿]"


def content_words(text, lang, nmin=2, nmax=4):
    """抽实词候选。CJK 用 n-gram（无分词器时最稳），拉丁系按空白切。
    只做候选抽取，不做词性判断——判断留给人。"""
    if lang in ("zh", "ja"):
        out = Counter()
        for run in re.findall(rf"{CJK}{{{nmin},}}", text):
            for n in range(nmin, nmax + 1):
                for i in range(len(run) - n + 1):
                    out[run[i:i + n]] += 1
        return out
    return Counter(w.lower() for w in re.findall(r"[A-Za-z][A-Za-z\-']{2,}", text))


def table_rows(path, ncol):
    rows = []
    for n, line in enumerate(open(path, encoding="utf-8"), 1):
        if not line.lstrip().startswith("|"):
            continue
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) <= ncol or set(c[0]) <= set("-: "):
            continue
        rows.append((n, c))
    return rows


def cmd_cover(a):
    src = open(a.file, encoding="utf-8").read()
    src = re.sub(r"^#.*$", "", src, flags=re.M)
    rows = table_rows(a.glossary, a.gloss_src_col)
    # 只认「词条本身」，不认复合词里的子串。
    # 踩过：术语表有「企业○○」，子串匹配就把「企业」判成已收 →
    # 但「企业」自己从没被裁定过，译文里 企業×2/法人×8 不统一，没有任何闸拦得住。
    heads = set()
    for _, c in rows:
        cell = c[a.gloss_src_col].strip("`*")
        head = re.split(r"[（(]", cell)[0]          # 去掉括号里的出现语境
        for part in re.split(r"[、,／/]", head):     # 一格里并列多个词条
            part = part.strip()
            if part:
                heads.add(part)
    if not rows:
        print("**术语表解析出 0 行。这不等于通过——多半是列号指错了。**")
        sys.exit(2)
    print(f"# term_coverage · 覆盖闸\n\n源文 `{a.file}` / 术语表 `{a.glossary}`（{len(rows)} 条，源语词取第 {a.gloss_src_col} 列）")
    print(f"\n**回显前 3 条术语表词条**，确认列号没指错：{sorted(heads)[:3]}\n")
    cnt = content_words(src, a.src_lang)
    # 去掉被更高频的更长词完全包含的短片段（n-gram 噪声）
    items = sorted(cnt.items(), key=lambda x: (-x[1], -len(x[0])))
    keep, seen = [], []
    for w, n in items:
        if n < a.min:
            continue
        if any(w in W and n <= N for W, N in seen):
            continue
        seen.append((w, n)); keep.append((w, n))
    miss = [(w, n) for w, n in keep if w not in heads]
    print(f"频次 ≥{a.min} 的实词候选 {len(keep)} 个，其中**术语表未收 {len(miss)} 个**\n")
    print("| 源语词 | 频次 | 术语表 |\n|---|---|---|")
    for w, n in keep[:40]:
        print(f"| `{w}` | {n} | {'—' if w in heads else '**未收**'} |")
    print("\n**未收 ≠ 一定要收。** 但频次高又反复出现在并列位置的词，"
          "不收就没有任何一道闸能保证它全篇统一——实测两个不一致的词都出在这里。"
          "决定不收的，在术语表里写一行「不需要统一，理由是…」，让下一个人看得见。")


def cmd_enforce(a):
    grows = table_rows(a.glossary, max(a.gloss_src_col, a.gloss_tgt_col))
    brows = table_rows(a.file, max(a.src_col, a.tgt_col))
    if not grows or not brows:
        print("**解析出 0 行。这不等于通过——多半是列号指错了。**")
        sys.exit(2)
    print(f"# term_coverage · 执行闸\n\n双语表 `{a.file}`（{len(brows)} 行）/ 术语表 `{a.glossary}`（{len(grows)} 条）")
    print(f"\n**回显前 2 条术语映射**：{[(c[a.gloss_src_col][:10], c[a.gloss_tgt_col][:10]) for _, c in grows[:2]]}\n")
    bad = []
    for _, g in grows:
        zh, ja = g[a.gloss_src_col].strip("`"), g[a.gloss_tgt_col].strip("`")
        if not zh or not ja or len(zh) < 2:
            continue
        hit = [c for _, c in brows if zh in c[a.src_col]]
        if not hit:
            continue
        ok = sum(1 for c in hit if ja in c[a.tgt_col])
        if ok < len(hit):
            bad.append((zh, ja, ok, len(hit),
                        [c[a.src_col][:1] and c[0] for c in hit if ja not in c[a.tgt_col]][:6]))
    print(f"命中源文的术语 {sum(1 for _,g in grows if g[a.gloss_src_col].strip('`'))} 条中，"
          f"**译文未照表用的 {len(bad)} 条**\n")
    if bad:
        print("| 术语表定的 | 目标语词 | 照用 / 命中 | 未照用的行号 |\n|---|---|---|---|")
        for zh, ja, ok, tot, rn in sorted(bad, key=lambda x: x[2] / x[3]):
            print(f"| `{zh}` | `{ja}` | {ok}/{tot} | {', '.join(map(str, rn))} |")
        print("\n**未照用不一定是错**——同一个源语词可能有多个义项，术语表也可能只管其中一个。"
              "但每一处都要能说出为什么，说不出就是漏了。")
    else:
        print("术语表定的词，译文全部照用。")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("cover"); c.add_argument("file"); c.add_argument("--glossary", required=True)
    c.add_argument("--src-lang", default="zh"); c.add_argument("--min", type=int, default=4)
    c.add_argument("--gloss-src-col", type=int, default=2); c.set_defaults(fn=cmd_cover)
    e = sub.add_parser("enforce"); e.add_argument("file"); e.add_argument("--glossary", required=True)
    e.add_argument("--src-col", type=int, default=2); e.add_argument("--tgt-col", type=int, default=3)
    e.add_argument("--gloss-src-col", type=int, default=2); e.add_argument("--gloss-tgt-col", type=int, default=3)
    e.set_defaults(fn=cmd_enforce)
    a = p.parse_args(); a.fn(a)


if __name__ == "__main__":
    main()
