#!/usr/bin/env python3
"""deliverable_check.py — 交付前自检：译文里有没有不该出现的东西。

用法:
  python3 deliverable_check.py <双语表.md> --target-locale ja-JP [--source-locale en-US]
                               [--src-col 2] [--tgt-col 3] [--markers '【要確認,TODO']
                               [--keep 'Acme,^\\d+K$']   # 有意不译的（品牌名、规格名、代码…）

检查项（全部语言无关）:
  1. 文字体系不符 —— 目标语该有的文字没有（例：ja/zh/ko 的单元格里没有 CJK）
  2. 源文残留 —— 译文栏与源文栏几乎相同
  3. 占位/标记泄漏 —— 待确认标记、TODO、方案脚手架混进译文
  4. 标记语言泄漏 —— HTML 标签、markdown 强调、内部指针
  5. 变量占位符不匹配 —— {name} %s {{x}} 在源译两侧数量或名称不一致
  6. 空译文

有意不译的内容（品牌名、规格名、代码、法人后缀）用 --keep 传正则，命中的降级为 note。
另：长度 < 6 且与源文相同的单元格自动降为 note（多为专有名词），不当作错误。

只报告不裁决。stdlib only。
"""
import argparse
import re
import sys
import unicodedata
from markdown_utils import emphasis_signature, table_rows

# 文字体系家族：语言前缀 -> 该语言正文必须出现的字符类
SCRIPTS = {
    "ja": ("CJK 或假名", re.compile(r"[぀-ヿ㐀-䶿一-鿿]")),
    "zh": ("汉字", re.compile(r"[㐀-䶿一-鿿]")),
    "ko": ("谚文", re.compile(r"[가-힣ᄀ-ᇿ]")),
    "th": ("泰文", re.compile(r"[฀-๿]")),
    "ar": ("阿拉伯文", re.compile(r"[؀-ۿ]")),
    "he": ("希伯来文", re.compile(r"[֐-׿]")),
    "ru": ("西里尔字母", re.compile(r"[Ѐ-ӿ]")),
    "el": ("希腊字母", re.compile(r"[Ͱ-Ͽ]")),
    "hi": ("天城文", re.compile(r"[ऀ-ॿ]")),
}
# 拉丁字母系：不做"必须出现"检查，改为检查是否混入了源语的非拉丁文字
LATIN_LIKE = {"en", "de", "fr", "es", "it", "pt", "nl", "sv", "da", "no", "fi", "pl", "cs", "tr", "id", "vi"}

DEFAULT_MARKERS = ["【要確認", "【待确认", "【TODO", "TODO:", "FIXME", "XXX:", "待确认", "要確認",
                   "（推荐", "(推荐", "**A**", "**B**", "见下方", "见文末", "見下記", "占位"]
MARKUP = [("<br>", "HTML 换行标签"), ("<br/>", "HTML 换行标签"), ("<br />", "HTML 换行标签"),
          ("</", "HTML 结束标签"), ("&nbsp;", "HTML 实体"), ("&amp;", "HTML 实体")]
PLACEHOLDER = re.compile(r"\{\{[^{}]+\}\}|\{[A-Za-z_][A-Za-z0-9_]*\}|%\d*\$?[sdifx]|%\([A-Za-z_]+\)[sdif]")


def script_of(locale):
    return (locale or "").split("-")[0].split("_")[0].lower()


def width(s):
    w = 0.0
    for ch in s:
        if unicodedata.combining(ch):
            continue
        w += 1.0 if unicodedata.east_asian_width(ch) in ("W", "F") else 0.55
    return w


def _table_blocks(path):
    blocks, current = [], []
    for n, cells in table_rows(path):
        if current and n != current[-1][0] + 1:
            blocks.append(current)
            current = []
        current.append((n, cells))
    if current:
        blocks.append(current)
    return blocks


def _candidate_rows(block, src_col, tgt_col):
    out = []
    for n, cells in block:
        if len(cells) <= max(src_col, tgt_col):
            continue
        ident = re.sub(r"^[`*_ ]+|[`*_ ]+$", "", cells[0])
        if not re.match(r"^[\w.\-\[\]/]+$", ident) or set(ident) <= set("-: "):
            continue
        if ident.lower() in ("key", "id", "元素", "编号", "序号", "行", "no", "num", "item"):
            continue
        out.append((n, ident, cells[src_col], cells[tgt_col]))
    return out


def _is_bilingual(rows, src_locale, tgt_locale):
    """判断这一块到底是不是双语表。

    信号：拿一个「有区分力的文字体系」，看它在源文列和译文列的出现比例。
    真双语表两列应当差得很开；两列都满是目标语文字，说明第二列不是源文列
    （典型：铁律 9 要求单独放的占位清单、纯目标语的成品表）。

    **只在文字体系真能区分这个语对时才用**：一边拉丁系、另一边非拉丁系。
    zh↔ja、ja↔ko 这种共用汉字的语对，两列本来就都是 CJK，这个信号无效，
    一律不拦（宁可多检几张表，不可漏掉真正的译文表）。
    """
    if len(rows) < 3 or not src_locale or not tgt_locale:
        return True, None
    sf, tf = script_of(src_locale), script_of(tgt_locale)
    # 恰好一边是已知非拉丁文字体系、另一边是拉丁系，才有区分力
    pairs = [(tf, "tgt"), (sf, "src")]
    fam, side = next(((f, s) for f, s in pairs if f in SCRIPTS), (None, None))
    other = sf if side == "tgt" else tf
    if fam is None or other not in LATIN_LIKE:
        return True, None
    rx = SCRIPTS[fam][1]
    sr = sum(1 for _, _, s, _ in rows if rx.search(s)) / len(rows)
    tr = sum(1 for _, _, _, tt in rows if rx.search(tt)) / len(rows)
    gap = (tr - sr) if side == "tgt" else (sr - tr)
    if gap < 0.4:
        return False, (f"第 {rows[0][0]} 行起的表：源文列与译文列的文字体系分不开"
                       f"（{SCRIPTS[fam][0]} 占比 源{sr:.0%} / 译{tr:.0%}），"
                       f"判定为非双语表，已跳过")
    return True, None


def parse_rows(path, src_col, tgt_col, src_locale=None, tgt_locale=None):
    rows, skipped = [], []
    for block in _table_blocks(path):
        cand = _candidate_rows(block, src_col, tgt_col)
        if not cand:
            continue
        ok, why = _is_bilingual(cand, src_locale, tgt_locale)
        if ok:
            rows.extend(cand)
        else:
            skipped.append((why, len(cand)))
    return rows, skipped


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--target-locale", required=True)
    ap.add_argument("--source-locale", default=None)
    ap.add_argument("--src-col", type=int, default=2, help="源文所在列（0 起）")
    ap.add_argument("--tgt-col", type=int, default=3, help="译文所在列（0 起）")
    ap.add_argument("--markers", default=None, help="额外的标记，逗号分隔")
    ap.add_argument("--keep", default=None, help="有意不译的正则，逗号分隔（品牌名/规格名/代码）")
    a = ap.parse_args()
    if min(a.src_col, a.tgt_col) < 0 or a.src_col == a.tgt_col:
        ap.error("源译列须为不同的非负整数。")

    markers = list(DEFAULT_MARKERS)
    if a.markers:
        markers += [m for m in a.markers.split(",") if m.strip()]

    keeps = [re.compile(k) for k in (a.keep.split(",") if a.keep else []) if k.strip()]
    tgt = script_of(a.target_locale)
    src = script_of(a.source_locale) if a.source_locale else None
    rows, skipped = parse_rows(a.file, a.src_col, a.tgt_col, a.source_locale, a.target_locale)

    findings = []   # (line, id, kind, msg, level)
    for n, ident, s, t in rows:
        raw = t.strip()
        # Compare markup before stripping it; text inside emphasis is translated.
        src_emphasis = emphasis_signature(s)
        tgt_emphasis = emphasis_signature(raw)
        if tgt_emphasis != src_emphasis:
            if tgt_emphasis and not src_emphasis:
                msg = f"译文新增 markdown 强调，源文没有对应标记：{raw[:40]}"
            else:
                msg = f"译文 markdown 强调与源文不对称（源 {src_emphasis} / 译 {tgt_emphasis}）：{raw[:40]}"
            findings.append((n, ident, "标记语言泄漏", msg, "error"))
        bare = re.sub(r"[*`_~]", "", t).strip()
        if bare in ("", "—", "-", "–", "N/A"):
            findings.append((n, ident, "空译文", "译文栏为空或占位横杠", "error"))
            continue

        kept = any(k.search(bare) for k in keeps)
        short_same = len(bare) < 6 and re.sub(r"\s+", "", s).lower() == re.sub(r"\s+", "", bare).lower()
        lvl_untr = "note" if (kept or short_same) else "error"

        # 1. 文字体系
        if tgt in SCRIPTS:
            name, rx = SCRIPTS[tgt]
            if not rx.search(bare):
                findings.append((n, ident, "文字体系不符", f"目标语 {a.target_locale} 应含{name}，本行没有：{bare[:40]}"
                                 + ("（疑为有意不译，确认即可）" if lvl_untr == "note" else ""), lvl_untr))
        elif tgt in LATIN_LIKE:
            for fam, (fname, frx) in SCRIPTS.items():
                if frx.search(bare):
                    findings.append((n, ident, "非目标语文字混入",
                                     f"目标语 {a.target_locale} 为拉丁系，却含{fname}：{bare[:40]}", lvl_untr))
                    break

        # 2. 源文残留
        ns = re.sub(r"\s+", "", re.sub(r"[*`_~]", "", s)).lower()
        nt = re.sub(r"\s+", "", bare).lower()
        if ns and nt and (ns == nt or (len(ns) > 12 and nt.startswith(ns[:int(len(ns) * 0.8)]))):
            findings.append((n, ident, "源文残留", f"译文栏与源文栏几乎相同：{bare[:40]}"
                             + ("（疑为有意不译，确认即可）" if lvl_untr == "note" else ""), lvl_untr))

        # Formatting symmetry does not exempt newly added editorial annotations.
        for annotation in ("（原文のまま）", "(原文のまま)", "（保留原文）"):
            if annotation in t and annotation not in s:
                findings.append((n, ident, "标记泄漏", f"新增处理说明 {annotation}", "error"))

        # 3. 标记泄漏
        for m in markers:
            if m in t:
                findings.append((n, ident, "标记泄漏", f"译文含 `{m}`，应移到独立列或清单", "error"))
                break

        # 4. 标记语言
        for m, why in MARKUP:
            if m in t:
                findings.append((n, ident, "标记语言泄漏", f"{why} `{m}` 混入译文", "error"))
                break

        # 5. 变量占位符
        ps, pt = sorted(PLACEHOLDER.findall(s)), sorted(PLACEHOLDER.findall(bare))
        if ps != pt:
            only_s = [p for p in ps if p not in pt]
            only_t = [p for p in pt if p not in ps]
            findings.append((n, ident, "占位符不匹配",
                             f"只在源文 {only_s or '—'}；只在译文 {only_t or '—'}", "error"))

    print("# deliverable_check 报告\n")
    print(f"文件: {a.file}")
    print(f"源 locale: {a.source_locale or '(未指定)'}　目标 locale: {a.target_locale}")
    print(f"检查行数: {len(rows)}")
    for why, cnt in skipped:
        print(f"跳过: {why}（{cnt} 行）")
    print()
    if not rows:
        print("**解析到 0 行，这不等于没有问题。** 可能原因：")
        print("- 文件不是 markdown 表格，或表格列数少于 --src-col/--tgt-col 所指")
        print("- ID 列的内容不像标识符（脚本按第 0 列判定数据行）")
        print("排查：确认表格首列是 key 或编号，并核对 --src-col / --tgt-col。")
        return 2
    errs = [f for f in findings if f[4] == "error"]
    notes = [f for f in findings if f[4] == "note"]

    # 防呆：列位指错时，症状是"全都空译文"，此时报错比逐行刷屏有用
    empty = [f for f in errs if f[2] == "空译文"]
    if rows and len(empty) >= max(2, int(len(rows) * 0.8)):
        sample = rows[0]
        print("# deliverable_check 报告\n")
        print(f"文件: {a.file}")
        print(f"**列位可能指错了**：{len(rows)} 行全部读到空译文。")
        print(f"当前 --src-col {a.src_col} --tgt-col {a.tgt_col}（列号从 0 起，第 0 列是 ID）。")
        with open(a.file, encoding="utf-8") as f:
            for line in f:
                if line.lstrip().startswith("|"):
                    cells = [c.strip() for c in line.strip().strip("|").split("|")]
                    if len(cells) > 1 and not set("".join(cells)) <= set("-: |"):
                        print("\n该文件的列布局（首个数据行）：")
                        for i, c in enumerate(cells):
                            print(f"  第 {i} 列: {c[:46]}")
                        break
        print("\n按上表重设 --src-col / --tgt-col 后重跑。")
        return 2
    if not errs and not notes:
        print("- 未发现本脚本检查范围内的问题；仍需语义审校。")
        return 0
    kinds = {}
    for _, _, k, _, lv in errs:
        kinds[k] = kinds.get(k, 0) + 1
    print(f"- 必须处理 {len(errs)} 项，{len(kinds)} 类；待确认 {len(notes)} 项")
    for k, v in sorted(kinds.items(), key=lambda x: -x[1]):
        print(f"  - {k}: {v}")
    print()
    for n, ident, kind, msg, _ in errs:
        print(f"- L{n} [{ident}] {kind} — {msg}")
    if notes:
        print("\n## 待确认（多为有意不译，确认后可忽略）")
        for n, ident, kind, msg, _ in notes:
            print(f"- L{n} [{ident}] {kind} — {msg}")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
