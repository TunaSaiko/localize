#!/usr/bin/env python3
"""length_estimate.py — 按行对齐估算显示宽度（em），只报告不裁决。

用法: python3 length_estimate.py <源文> <译文> [--max-em N] [--halfwidth-em 0.55]
      python3 length_estimate.py --siblings <双语表> [--key-col 1] [--tgt-col 3]
        平行组模式：把 key 里只有一个 token 变化的条目（如 plan_lite_/standard_/pro_/max_description，示意）
        归成一组，列出组内显示宽度的极差。**只列不判**——阈值定在几倍没有跨项目依据。
        用途：组级发现（"这几条不齐"）不能靠改一个成员来修，见 SKILL.md §5.6。
全角（East Asian Width W/F）按 1.0 em，其余按 --halfwidth-em（默认 0.55），组合字符 0。
中日英之间的风险不是字符数膨胀，是显示宽度和行高；短串膨胀率最高。最终以渲染为准。
"""
import sys
import unicodedata


def width(s, half):
    w = 0.0
    for ch in s:
        if unicodedata.combining(ch):
            continue
        eaw = unicodedata.east_asian_width(ch)
        w += 1.0 if eaw in ("W", "F") else half
    return w


def siblings_mode(path, kc, tc, half):
    import collections, re as _re
    g = collections.defaultdict(list)
    rows = 0
    for line in open(path, encoding="utf-8"):
        if not line.lstrip().startswith("|"):
            continue
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) <= max(kc, tc) or set(c[0]) <= set("-: "):
            continue
        k, t = c[kc].strip("`"), c[tc]
        if not k or not t or "{" in t:      # 含占位符的宽度不可比，跳过
            continue
        if " " in k or "." not in k:        # 表头行、非 key 行
            continue
        rows += 1
        seg = k.split(".")
        for i, sg in enumerate(seg):        # 把含数字的那一段抽象成 N，即为平行组
            if _re.search(r"\d", sg):
                g[".".join(seg[:i] + [_re.sub(r"\d+", "N", sg)] + seg[i + 1:])].append((sg, t))
                break
    print("# length_estimate 平行组报告\n")
    print(f"文件 {path}（key 第 {kc} 列 / 译文第 {tc} 列）；解析 {rows} 行，含占位符的已跳过")
    groups = {k: v for k, v in g.items() if len(v) >= 3}
    if not rows:
        print("\n**解析出 0 行。这不等于通过——多半是列号指错了。**"); sys.exit(2)
    # 列号指错时行数照样不为 0，会静默出错结果——所以必须回显解析到的东西让人一眼看出来
    sample = [(k, v[0]) for k, v in list(g.items())[:3]]
    print("\n**回显前 3 组解析结果，确认列号没指错：**")
    for k, (sg, t) in sample:
        print(f"- 组 `{k}` ← 成员 `{sg}`，译文 `{t[:36]}`")
    print(f"\n平行组 {len(groups)} 个（成员 ≥3 才算）\n")
    print("| 平行组 | 成员 | 最窄 em | 最宽 em | 极差倍数 |")
    print("|---|---|---|---|---|")
    detail = []
    for k, v in sorted(groups.items(), key=lambda x: -(max(width(t, half) for _, t in x[1])
                                                       / max(min(width(t, half) for _, t in x[1]), 1e-9))):
        ws = [width(t, half) for _, t in v]
        lo, hi = min(ws), max(ws)
        r = hi / lo if lo else float("inf")
        print(f"| `{k}` | {len(v)} | {lo:.1f} | {hi:.1f} | **{r:.2f}×** |")
        detail.append((k, v, half))
    print("\n倍数大不自动等于错——有的组本来就该长短不一。但**组内明显有一条比同伴长出一截时，"
          "先看它是不是被单独改过**（改一个成员修不了组级问题，反而制造新的离群项）。\n")
    for k, v, h in detail:
        print(f"<details><summary><code>{k}</code></summary>\n")
        for sg, t in v:
            print(f"- `{sg}` {width(t, h):.1f}em  {t}")
        print("\n</details>")
    return


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", nargs="?"); ap.add_argument("target", nargs="?")
    ap.add_argument("--siblings"); ap.add_argument("--key-col", type=int, default=1)
    ap.add_argument("--tgt-col", type=int, default=3)
    ap.add_argument("--max-em", type=float, default=None)
    ap.add_argument("--halfwidth-em", type=float, default=0.55)
    a = ap.parse_args()
    max_em, half = a.max_em, a.halfwidth_em
    if a.siblings:
        return siblings_mode(a.siblings, a.key_col, a.tgt_col, half)
    if not a.source or not a.target:
        ap.error("需要 <源文> <译文> 两个文件，或用 --siblings <双语表>")
    with open(a.source, encoding="utf-8") as f:
        src = [l for l in f.read().splitlines() if l.strip()]
    with open(a.target, encoding="utf-8") as f:
        tgt = [l for l in f.read().splitlines() if l.strip()]
    print("# length_estimate 报告\n")
    print(f"源文 {len(src)} 非空行 / 译文 {len(tgt)} 非空行" + ("  ← 行数不等，按序号对齐仅供参考" if len(src) != len(tgt) else ""))
    print(f"半角按 {half} em，全角按 1.0 em\n")
    print("| 行 | 源字符 | 译字符 | 源 em | 译 em | 宽度比 | 备注 |")
    print("|---|---|---|---|---|---|---|")
    tot_s = tot_t = 0.0
    over = []
    worst = (0, 0.0)
    for i in range(max(len(src), len(tgt))):
        s = src[i] if i < len(src) else ""
        t = tgt[i] if i < len(tgt) else ""
        ws, wt = width(s, half), width(t, half)
        tot_s += ws; tot_t += wt
        ratio = (wt / ws) if ws else 0.0
        note = ""
        if max_em is not None and wt > max_em:
            note = f"超限 {wt - max_em:.1f} em"
            over.append(i + 1)
        if ratio > worst[1]:
            worst = (i + 1, ratio)
        print(f"| {i+1} | {len(s)} | {len(t)} | {ws:.1f} | {wt:.1f} | {ratio:.2f} | {note} |")
    print(f"\n- 总宽度比（译/源）: {tot_t / tot_s:.2f}" if tot_s else "")
    print(f"- 膨胀最大的行: L{worst[0]}（{worst[1]:.2f}）")
    if max_em is not None:
        print(f"- 超过 {max_em} em 的行: {over if over else '无'}")
    print("- 提醒：溢出时先找更短的原生说法，再改字号、框位、布局。改完必须导出最终格式逐页看。")


if __name__ == "__main__":
    main()
