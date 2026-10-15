#!/usr/bin/env python3
"""char_lint.py — 字符级规范扫描（按 locale，只报告不裁决）。

用法: python3 char_lint.py <文件> --locale ja-JP|zh-CN|zh-TW|en-US|en-GB [--space jtf|ms|on|off|report] [--software]
                             [--tgt-col N]   # 双语表：只检第 N 列（0 起）的译文，其余列与正文一律不检

双语表**必须**加 --tgt-col，否则源文列和你自己的注释列也会被当译文检，
误报会淹掉真问题（英文原文里的 `...` 和 `Sources :` 都会被报成日语标点错误）。
stdlib only。输出 markdown，含行号。
"""
import re
import sys
from collections import Counter
from markdown_utils import link_labels, table_rows

CJK = r"[぀-ヿ㐀-䶿一-鿿豈-﫿]"
KATA = r"[ァ-ヺ]"
ALNUM = r"[A-Za-z0-9]"


def parse_args():
    args = sys.argv[1:]
    if not args or args[0].startswith("--"):
        print(__doc__)
        sys.exit(2)
    path = args[0]
    opts = {"locale": "ja-JP", "space": "report", "software": False, "tgt_col": None}
    i = 1
    while i < len(args):
        if args[i] == "--locale":
            opts["locale"] = args[i + 1]; i += 2
        elif args[i] == "--space":
            opts["space"] = args[i + 1]; i += 2
        elif args[i] == "--software":
            opts["software"] = True; i += 1
        elif args[i] == "--tgt-col":
            opts["tgt_col"] = int(args[i + 1]); i += 2
        else:
            i += 1
    return path, opts


def findings_common(lines):
    out = []
    for n, line in enumerate(lines, 1):
        if "  " in line.strip():
            out.append((n, "minor", "连续空格", line.strip()[:60]))
        if re.search(r"[A-Za-z0-9] [,.;:!?]", line):
            out.append((n, "minor", "标点前有空格", line.strip()[:60]))
        if re.search(r"[０-９Ａ-Ｚａ-ｚ]", line):
            out.append((n, "minor", "全角英数字（改半角）", line.strip()[:60]))
        if re.search(r"[^\s] [，。、；：？！）」』]", line):
            out.append((n, "minor", "全角标点前有空格", line.strip()[:60]))
    return out


def findings_ja(lines, opts):
    out = []
    space_with, space_without = 0, 0
    for n, line in enumerate(lines, 1):
        s = line.strip()[:60]
        prose = link_labels(line)
        if "·" in line or "•" in line:
            out.append((n, "minor", "中黑用了 U+00B7/U+2022，日语用「・」U+30FB", s))
        if "～" in line:
            out.append((n, "minor", "全角波线 U+FF5E，区间号正解 U+301C「〜」" + ("；软件字符串禁用全角波线，改「から」或半角 -" if opts["software"] else ""), s))
        if opts["software"] and "〜" in line:
            out.append((n, "minor", "软件字符串出现全角波线 U+301C，改「から」或半角 -", s))
        if re.search(r"\d\s?~\s?\d", line):
            out.append((n, "minor", "数字间 ASCII ~，日语区间用「〜」U+301C", s))
        if re.search(r"\d\s?–\s?\d", line):
            out.append((n, "minor", "数字间 en dash，日语区间用「〜」", s))
        if re.search(r"約\s?[〜～~]", line):
            out.append((n, "minor", "「約」后接波线；「〜」不表示大约，写「約100」", s))
        if re.search(r"[｡-ﾟ]", line):
            out.append((n, "minor", "半角片假名", s))
        if re.search(rf"{KATA}(一|1|１)(?={KATA}|$|[、。」）\s])", line):
            out.append((n, "minor", "片假名后接「一/1」，疑为长音「ー」误写", s))
        if re.search(rf"{CJK}\s?[,.]\s?{CJK}", line):
            out.append((n, "minor", "CJK 之间用了 ASCII 逗号/句号，日语用「、」「。」", s))
        if re.search(r"\.\.\.", line):
            out.append((n, "minor", "三个 ASCII 点，省略号用「…」U+2026", s))
        # bracket mix
        if re.search(rf"{CJK}\(", prose) or re.search(rf"\){CJK}", prose):
            out.append((n, "minor", "日语文本中半角括号（全篇统一：全角（））", s))
        # space policy
        space_with += len(re.findall(rf"{CJK} {ALNUM}", line)) + len(re.findall(rf"{ALNUM} {CJK}", line))
        space_without += len(re.findall(rf"{CJK}{ALNUM}", line)) + len(re.findall(rf"{ALNUM}{CJK}", line))
        if opts["space"] == "jtf" and re.search(rf"{CJK} {ALNUM}|{ALNUM} {CJK}", line):
            out.append((n, "minor", "JTF 策略：全角与半角之间不加空格", s))
        if opts["space"] == "ms" and re.search(rf"{CJK}{ALNUM}|{ALNUM}{CJK}", line):
            out.append((n, "minor", "Microsoft 策略：全角与半角之间加半角空格", s))
    summary = f"全角/半角之间：有空格 {space_with} 处，无空格 {space_without} 处（策略 --space {opts['space']}；JTF 不加 / Microsoft 加，只求全篇统一）"
    out += _ja_sentence_period(lines)
    return out, summary


# 「完整句式的短状态句，结尾带不带「。」」——同一份 UI 里必须一致。
# 这是数一数就知道的事实（铁律 5），不该等母语者用肉眼从一条字符串里推出来。
# 实测（某真实项目）：长正文 45/45 全带「。」，分裂全部集中在 37 条短状态句，21 带 / 16 不带。
_JA_SENT_END = re.compile(r"(ます|ました|ません|でした|です|ください|下さい)$")


def _ja_sentence_period(lines, short_em=26.0):
    """启发式分类，不是语法分析：
    ① 去掉 {占位符} 后以です・ます系结尾 → 算完整句式（体言止め的按钮/标签不入选）
    ② 内部无「。」且显示宽度 ≤ short_em → 算「短状态句」（长正文另算，两类惯例本就不同）
    只输出少数派那一侧，两侧都非空才输出——多数派即事实上的惯例。"""
    have, lack = [], []
    for n, line in enumerate(lines, 1):
        t = re.sub(r"\{[^{}]*\}", "", line).strip()
        if not t:
            continue
        core = t[:-1] if t.endswith("。") else t
        if "。" in core or not _JA_SENT_END.search(core):
            continue
        if sum(1.0 if ord(c) > 0x2E80 else 0.55 for c in t) > short_em:
            continue
        (have if t.endswith("。") else lack).append((n, t[:50]))
    if not have or not lack:
        return []
    minority, mark = (have, "带「。」") if len(have) <= len(lack) else (lack, "不带「。」")
    tip = (f"短状态句的结尾句点不统一：带「。」{len(have)} 条 / 不带 {len(lack)} 条，"
           f"以下是少数派（{mark}）。先定一条惯例，再全体对齐——两种写法本身都对，混用才是问题")
    return [(n, "minor", tip, s) for n, s in minority]


def findings_zh(lines, opts, tw=False):
    out = []
    space_with, space_without = 0, 0
    for n, line in enumerate(lines, 1):
        s = line.strip()[:60]
        if re.search(rf"{CJK}[,.?!;:]\s", line) or re.search(rf"{CJK}[,.?!;:]$", line.rstrip()):
            out.append((n, "minor", "CJK 后用了半角标点（文档用全角；软件 UI 体例另定）", s))
        if not tw and ("「" in line or "」" in line):
            out.append((n, "note", "直角引号「」：GB/T 15834 横排用“”，「」用于竖排（项目决定采用则忽略）", s))
        if tw and ("“" in line or "”" in line):
            out.append((n, "note", "zh-TW 引号惯用「」『』", s))
        if re.search(r"[A-Za-z0-9] [，。；：？！、）]", line) or re.search(r"[，。；：？！、（] [A-Za-z0-9]", line):
            out.append((n, "minor", "英文与中文标点之间有空格（CY/T 154 §8.2：不设空格）", s))
        if re.search(r"\d\s?~\s?\d", line):
            out.append((n, "minor", "数字间 ASCII ~，GB/T 15835 用「～」或「-」", s))
        m = re.search(r"\d+(?:\.\d+)?\s?[~～\-–]\s?\d+(?:\.\d+)?(亿|万|千|百万|%|％)", line)
        if m and not re.search(r"\d+(?:\.\d+)?(亿|万|千|百万|%|％)\s?[~～\-–]", line):
            out.append((n, "minor", f"范围「{m.group(0)}」：GB/T 15835 单位/百分号应两端都写（9亿～16亿）", s))
        if re.search(r"\.\.\.", line) or re.search(r"(?<!…)…(?!…)", line):
            out.append((n, "minor", "省略号应为「……」六点", s))
        space_with += len(re.findall(rf"{CJK} {ALNUM}", line)) + len(re.findall(rf"{ALNUM} {CJK}", line))
        space_without += len(re.findall(rf"{CJK}{ALNUM}", line)) + len(re.findall(rf"{ALNUM}{CJK}", line))
        if opts["space"] == "off" and re.search(rf"{CJK} {ALNUM}|{ALNUM} {CJK}", line):
            out.append((n, "minor", "项目策略：中英之间不加空格", s))
        if opts["space"] == "on" and re.search(rf"{CJK}{ALNUM}|{ALNUM}{CJK}", line):
            out.append((n, "minor", "项目策略：中英之间加空格", s))
    summary = f"中文/英数字之间：有空格 {space_with} 处，无空格 {space_without} 处（CY/T 154：可选但须全篇统一；策略 --space {opts['space']}）"
    return out, summary


def findings_en(lines, opts, gb=False):
    out = []
    straight = curly = ize = ise = 0
    for n, line in enumerate(lines, 1):
        s = line.strip()[:60]
        straight += line.count('"')
        curly += line.count("“") + line.count("”")
        ize += len(re.findall(r"\b\w+ize[sd]?\b", line))
        ise += len(re.findall(r"\b\w+ise[sd]?\b", line))
        if re.search(r"[　-ヿ一-鿿]", line):
            out.append((n, "minor", "英文文本中残留 CJK 字符", s))
        if gb and re.search(r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, \d{4}", line):
            out.append((n, "minor", "en-GB 日期应为「3 September 2026」（无逗号）", s))
        if not gb and re.search(r"\b\d{1,2} (?:January|February|March|April|May|June|July|August|September|October|November|December) \d{4}", line):
            out.append((n, "note", "「3 September 2026」是 en-GB 格式；en-US 用「September 3, 2026」", s))
    summary = f"引号：直引号 {straight} / 弯引号 {curly}（全篇统一）；-ize {ize} / -ise {ise}（{'en-GB' if gb else 'en-US'} 拼写体系提示）；序列逗号与引号内外标点无法自动判，人工核对"
    return out, summary


def main():
    path, opts = parse_args()
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    if opts["tgt_col"] is not None:
        c = opts["tgt_col"]
        if c < 0:
            print("列号必须为非负整数。")
            sys.exit(2)
        kept = 0
        scoped = [""] * len(lines)
        for n, cells in table_rows(path):
            if len(cells) > c:
                scoped[n - 1] = cells[c]
                kept += 1
        lines = scoped
        if kept == 0:
            print(f"**第 {c} 列取到 0 个单元格。这不等于没问题——多半是列号指错了。**")
            sys.exit(2)
        print(f"（只检第 {c} 列，取到 {kept} 个单元格）\n")
    loc = opts["locale"]
    out = findings_common(lines)
    if loc.startswith("ja"):
        o, summary = findings_ja(lines, opts)
    elif loc == "zh-TW":
        o, summary = findings_zh(lines, opts, tw=True)
    elif loc.startswith("zh"):
        o, summary = findings_zh(lines, opts)
    elif loc == "en-GB":
        o, summary = findings_en(lines, opts, gb=True)
    elif loc.startswith("en"):
        o, summary = findings_en(lines, opts)
    else:
        o, summary = [], f"locale {loc} 无规则包，只跑通用检查（降级）"
    out += o
    out.sort()
    print(f"# char_lint 报告\n\n文件: {path}  locale: {loc}  software: {opts['software']}\n")
    print(f"- {summary}")
    kinds = Counter(k for _, _, k, _ in out)
    print(f"- 发现: {len(out)} 项，{len(kinds)} 类\n")
    for n, lvl, kind, s in out:
        print(f"- L{n} [{lvl}] {kind}  … `{s}`")


if __name__ == "__main__":
    main()
