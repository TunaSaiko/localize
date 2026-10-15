#!/usr/bin/env python3
"""adapt_check.py — adapt 授权门与多对多事实映射的机械校验。只查可判定的，不做语义裁决。

用法:
  python3 adapt_check.py gate --authorization <授权表> --structure <结构方案> --conventions <市场惯例> [--map <adapt-map>]
  python3 adapt_check.py map  --source <源文> --ledger <事实账本> --map <adapt-map> --draft <目标稿> --authorization <授权表> [--glossary <术语表>]

退出码: 0 通过 / 1 映射或事实落地有阻塞发现 / 2 授权门不通过（不得生成）

覆盖边界（每次输出都会重申）：
- 本脚本只验证「声明的目标实现串是否逐字出现在指定目标单元」，不判断该串语义上是否真的表达了那个颗粒。
- 语义是否保住，仍归 subagent 模板 F 的独立审校和作者验收；脚本通过不等于 adapt 通过。
stdlib only。
"""
import argparse
import hashlib
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from markdown_utils import is_separator, split_cells  # noqa: E402
import fact_check  # noqa: E402

GRANULES = ["主体", "对象", "动作/关系", "数量/单位", "时间", "情态/确定性",
            "否定/限制/条件", "功能/价格/法律承诺"]
IDENTITY_GRANULES = {"主体", "对象"}          # 需要与术语表定译对齐的颗粒
GLOSSARY_REQUIRED = {"主体"}                  # 缺定译就阻塞的颗粒（受益人错＝critical）
RE_ANCHOR = re.compile(r"<!--\s*((?:SRC|TGT)-\d+)\s*-->")
RE_COMMENT = re.compile(r"<!--.*?-->", re.S)
RE_UNIT_ID = re.compile(r"(?:SRC|TGT)-\d+")
RE_AUTH_ID = re.compile(r"AUTH-\d+")
RE_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
RE_LIST_MARKER = re.compile(r"^\s*(?:#{1,6}\s+|>\s*|[-*+]\s+|\d+[.)]\s+)", re.M)
RE_FOOTNOTE_MARK = re.compile(r"[＊*※]\s*\d+")


def fact_view(text):
    """数字/日期比较用的视图：去掉结构性编号，只留事实里的数字。

    AUTH-08 授权的「散文 → 编号步骤」会让目标稿多出 1. 2. 3.，脚注记号 ＊1 ＊2 同理。
    这些是版式，不是事实。不剥掉的话，闸门会拦住它自己授权的那个改写。
    URL 不动——URL 的比较走原文，那里的数字必须逐位对上。
    """
    text = RE_COMMENT.sub("", text)
    text = RE_LIST_MARKER.sub("", text)
    return RE_FOOTNOTE_MARK.sub("", text)


def read(path):
    return Path(path).read_text(encoding="utf-8")


def nfkc(s):
    return unicodedata.normalize("NFKC", s)


def plain(s):
    """去掉粗体标记和首尾空白，用于读表格里的状态、裁决这类短值。"""
    return re.sub(r"[*_`]", "", s).strip()


def unfilled(value):
    v = plain(value)
    return v == "" or bool(re.fullmatch(r"<[^>]*>", v)) or v in {"—", "-", "–", "待定", "待答"}


def read_tables(path):
    """返回文件里所有 markdown 表：{'headers': [...], 'rows': [(行号, [单元格...])]}。"""
    lines = read(path).splitlines()
    tables, fence, i = [], None, 0
    while i < len(lines):
        line = lines[i]
        marker = RE_FENCE.match(line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence) and not line[marker.end():].strip():
                fence = None
            i += 1
            continue
        if (not fence and line.lstrip().startswith("|")
                and i + 1 < len(lines) and is_separator(lines[i + 1])):
            headers = [plain(h) for h in split_cells(line)]
            rows, j = [], i + 2
            while j < len(lines) and lines[j].lstrip().startswith("|") and not is_separator(lines[j]):
                rows.append((j + 1, split_cells(lines[j])))
                j += 1
            tables.append({"headers": headers, "rows": rows})
            i = j
            continue
        i += 1
    return tables


def pick_table(tables, *needed):
    for t in tables:
        if all(any(h == n for h in t["headers"]) for n in needed):
            return t
    return None


def cell(table, cells, name):
    try:
        idx = table["headers"].index(name)
    except ValueError:
        return ""
    return cells[idx] if idx < len(cells) else ""


def header_field(text, name):
    m = re.search(rf"{re.escape(name)}[：:]\s*([^\s　|]+)", text)
    return m.group(1).strip() if m else ""


def units(text, prefix):
    """按 <!-- SRC-001 --> / <!-- TGT-001 --> 锚点切分，只收 prefix 那一类，返回 {id: 单元正文}。

    目标稿里混进 SRC 锚点是常见手滑（照抄源文），不能让它变成假的「目标单元没有来源」。
    """
    out, marks = {}, list(RE_ANCHOR.finditer(text))
    for n, m in enumerate(marks):
        end = marks[n + 1].start() if n + 1 < len(marks) else len(text)
        if m.group(1).startswith(prefix):
            out[m.group(1)] = RE_COMMENT.sub("", text[m.end():end]).strip()
    return out


class Report:
    def __init__(self, title):
        self.title = title
        self.blocks = []
        self.warns = []
        self.notes = []

    def block(self, code, msg):
        self.blocks.append((code, msg))

    def warn(self, code, msg):
        self.warns.append((code, msg))

    def note(self, msg):
        self.notes.append(msg)

    def emit(self, fail_code):
        print(f"# {self.title}\n")
        for n in self.notes:
            print(f"- {n}")
        print("\n## 阻塞发现")
        if not self.blocks:
            print("- 无。")
        for code, msg in self.blocks:
            print(f"- **[{code}]** {msg}")
        print("\n## 需人工确认（不阻塞）")
        if not self.warns:
            print("- 无。")
        for code, msg in self.warns:
            print(f"- [{code}] {msg}")
        print("\n## 覆盖边界")
        print("- 只验证声明的目标实现串是否逐字出现在指定目标单元，不判断该串语义上是否真表达了那个颗粒。")
        print("- **目标侧覆盖只到单元级**：保证每个目标单元有来源，不保证单元内部每句话都有来源。句级加戏查不出来。")
        print("- 脚本通过 ≠ adapt 通过；语义保全归模板 F 独立审校，结构与体裁归作者验收。")
        print(f"\n## 汇总\n- 阻塞 {len(self.blocks)} 项 / 需人工确认 {len(self.warns)} 项")
        if self.blocks:
            print(f"- 结论：不通过（退出码 {fail_code}）")
            return fail_code
        print("- 结论：本脚本覆盖范围内未发现阻塞项（退出码 0）")
        return 0


# --------------------------------------------------------------------------- gate
def run_gate(a):
    rep = Report("adapt 授权门检查（A3→A4）")
    for label, path in (("授权表", a.authorization), ("结构方案", a.structure), ("市场惯例", a.conventions)):
        if not Path(path).exists():
            rep.block("G0", f"{label}不存在：{path}。开始前必须具备的三样缺一不可，不得生成。")
    if rep.blocks:
        return rep.emit(2)
    rep.note(f"授权表：{a.authorization}")
    rep.note(f"结构方案：{a.structure}")
    rep.note(f"市场惯例：{a.conventions}")
    rep.note("**本闸只能验证批准事件被记录下来了，不能验证它真的发生过。**"
             "作者确认栏是谁填的，只有作者本人能判断——交付前请作者自己看一眼这两张表。")

    auth_text = read(a.authorization)
    auth_tbl = pick_table(read_tables(a.authorization), "编号")
    approved = {}
    if auth_tbl is None:
        rep.block("G1", "授权表里找不到带「编号」列的表，无法判定授权状态。")
    else:
        status_col = next((h for h in auth_tbl["headers"] if h.startswith("状态")), "")
        confirm_col = next((h for h in auth_tbl["headers"] if "作者确认" in h), "")
        for line, cells in auth_tbl["rows"]:
            code = plain(cell(auth_tbl, cells, "编号"))
            status = plain(cell(auth_tbl, cells, status_col))
            confirm = cell(auth_tbl, cells, confirm_col)
            if code == "AUTH-07":
                if "禁止" not in status:
                    rep.block("G1", f"第 {line} 行：AUTH-07（事实层）状态为「{status}」。事实层动作永远不可授权。")
                continue
            if status == "已授权":
                if unfilled(confirm):
                    rep.block("G2", f"第 {line} 行：{code} 标为已授权，但没有作者确认事件。模型不能自填批准。")
                else:
                    approved[code] = confirm.strip()
        if not approved:
            rep.block("G3", "授权表里没有任何已授权的表达层动作，不构成 adapt 前提。")

    scope = re.search(r"作者批准的范围[：:]\s*(.*)", auth_text)
    if not scope or unfilled(scope.group(1)):
        rep.block("G4", "「授权结论 / 作者批准的范围」为空或仍是占位符。")

    stru_tbl = pick_table(read_tables(a.structure), "项目", "结果")
    plan = ""
    if stru_tbl is None:
        rep.block("G5", "结构方案里找不到「作者裁决」表（需要「项目 | 结果」两列）。")
    else:
        verdict = {plain(cell(stru_tbl, c, "项目")): cell(stru_tbl, c, "结果") for _, c in stru_tbl["rows"]}
        plan = plain(verdict.get("批准方案", ""))
        if plan in {"", "不批准"} or "/" in plan or unfilled(plan):
            rep.block("G5", f"批准方案为「{plan or '空'}」。作者未批准具体方案前不得生成。")
            plan = ""
        elif not re.search(rf"^#{{1,6}}\s*方案\s*{re.escape(plan)}\s*[:：]", read(a.structure), re.M):
            # 方案名不限于单个字母（A''、A-2、案A 都常见），但必须真的对应文件里的一个方案小节
            rep.block("G5", f"批准方案「{plan}」在本文件里找不到对应的「## 方案 {plan}：…」小节。"
                            "批准了一个不存在的方案，生成侧无从照办。")
        if unfilled(verdict.get("作者确认/日期", "")):
            rep.block("G6", "结构方案缺作者确认/日期。批准必须是真实事件，不能由模型补写。")

    conv_tables = read_tables(a.conventions)
    conv_tbl = pick_table(conv_tables, "CONV")
    if conv_tbl is None:
        rep.block("G7", "市场惯例文件里找不到带「CONV」列的表。")
    else:
        samples, sample_tbl = {}, None
        for t in conv_tables:
            if t is not conv_tbl and any("读者画像" in h for h in t["headers"]):
                sample_tbl = t
                break
        if sample_tbl is not None:
            # 两表式：样本单独一张表，惯例按 S 编号引用（记得下原生/翻译，单表式记不下）
            s_url = next((h for h in sample_tbl["headers"] if "URL" in h.upper()), "")
            s_reader = next((h for h in sample_tbl["headers"] if "读者画像" in h), "")
            s_use = next((h for h in sample_tbl["headers"] if "作依据" in h), "")
            for _, c in sample_tbl["rows"]:
                sid = plain(c[0]) if c else ""
                m = re.search(r"S\d+", sid)
                if not m:
                    continue
                verdict_cell = plain(cell(sample_tbl, c, s_use)) if s_use else ""
                samples[m.group(0)] = {
                    "url": not unfilled(cell(sample_tbl, c, s_url)),
                    "reader": not unfilled(cell(sample_tbl, c, s_reader)),
                    "usable": not any(x in verdict_cell for x in ("❌", "不可", "不能")),
                }
            rep.note(f"样本表：{len(samples)} 份，其中可作依据 "
                     f"{sum(1 for v in samples.values() if v['usable'] and v['url'] and v['reader'])} 份")

        url_col = next((h for h in conv_tbl["headers"] if "URL" in h.upper()), "")
        reader_col = next((h for h in conv_tbl["headers"] if "读者画像" in h), "")
        ok = []
        for _, c in conv_tbl["rows"]:
            if plain(cell(conv_tbl, c, "验证状态")) != "已验证":
                continue
            inline = (url_col and reader_col
                      and not unfilled(cell(conv_tbl, c, url_col))
                      and not unfilled(cell(conv_tbl, c, reader_col)))
            refs = [samples[s] for s in re.findall(r"S\d+", " ".join(c)) if s in samples]
            if inline or any(s["usable"] and s["url"] and s["reader"] for s in refs):
                ok.append(c)
        if not ok:
            rep.block("G7", "没有一条惯例同时满足「已验证 + 有样本 URL + 有读者画像」。"
                            "样本可以写在惯例行里，也可以单列样本表、惯例行引用 S 编号；"
                            "两种都没有时，只能停止 adapt 或降级 translate。")
        else:
            rep.note(f"可用惯例：{len(ok)} 条（已验证且追得到读者画像）")

    if a.map:
        if not Path(a.map).exists():
            rep.block("G8", f"adapt-map 不存在：{a.map}")
        else:
            map_text = read(a.map)
            map_plan = header_field(map_text, "批准方案")
            if plan and map_plan and map_plan != plan:
                rep.block("G8", f"adapt-map 头部批准方案「{map_plan}」与作者裁决「{plan}」不一致。")
            map_tbl = pick_table(read_tables(a.map), "MAP", "源单元集合")
            if map_tbl is None:
                rep.block("G8", "adapt-map 里找不到带「MAP | 源单元集合」的映射表。")
            else:
                basis_col = next((h for h in map_tbl["headers"] if "授权" in h), "")
                kind_col = next((h for h in map_tbl["headers"] if "重构类型" in h), "")
                for line, cells in map_tbl["rows"]:
                    mid = plain(cell(map_tbl, cells, "MAP"))
                    refs = RE_AUTH_ID.findall(cell(map_tbl, cells, basis_col))
                    kind = plain(cell(map_tbl, cells, kind_col))
                    if not refs and kind != "无结构变化":
                        rep.block("G9", f"第 {line} 行：{mid} 没有引用任何 AUTH 编号，结构变化无授权依据。"
                                        "确实没动结构的行，重构类型写「无结构变化」。")
                    for r in refs:
                        if r == "AUTH-07":
                            rep.block("G9", f"第 {line} 行：{mid} 引用了 AUTH-07（事实层），永远禁止。")
                        elif r not in approved:
                            rep.block("G9", f"第 {line} 行：{mid} 引用 {r}，但该动作未获授权。")
    return rep.emit(2)


# --------------------------------------------------------------------------- map
def check_hash(rep, source_path, label, path):
    actual = hashlib.sha256(Path(source_path).read_bytes()).hexdigest()
    recorded = header_field(read(path), "源文哈希")
    if not recorded or unfilled(recorded):
        rep.block("M0", f"{label}没有登记源文哈希，无法证明它是对着这份源文建的。")
    elif len(recorded) < 8 or not actual.startswith(recorded.lower()):
        rep.block("M0", f"{label}登记的源文哈希 `{recorded}` 与实际源文 `{actual[:12]}` 不符。"
                        "账本必须在 A2 对着源文冻结，不能在生成后回头改。")


def run_map(a):
    rep = Report("adapt 事实映射检查（A4→A5）")
    missing = [(l, p) for l, p in (("源文", a.source), ("事实账本", a.ledger), ("adapt-map", a.map),
                                   ("目标稿", a.draft), ("授权表", a.authorization)) if not Path(p).exists()]
    for label, path in missing:
        rep.block("M0", f"{label}不存在：{path}")
    if rep.blocks:
        return rep.emit(1)

    src_text, draft_text = read(a.source), read(a.draft)
    src_units, tgt_units = units(src_text, "SRC"), units(draft_text, "TGT")
    for label, text, wrong in (("源文", src_text, "TGT"), ("目标稿", draft_text, "SRC")):
        stray = sorted({m.group(1) for m in RE_ANCHOR.finditer(text) if m.group(1).startswith(wrong)})
        if stray:
            rep.block("M1", f"{label}里出现了 {wrong} 锚点：{'、'.join(stray)}。锚点用错前缀，单元归属会算错。")
    rep.note(f"源文 {a.source}：{len(src_units)} 个源单元")
    rep.note(f"目标稿 {a.draft}：{len(tgt_units)} 个目标单元")
    rep.note("单元数不等不算漏译，逐条按事实落地表核对。")
    if not src_units:
        rep.block("M1", "源文里没有 `<!-- SRC-00x -->` 锚点，无法做单元级映射核对。")
    if not tgt_units:
        rep.block("M1", "目标稿里没有 `<!-- TGT-00x -->` 锚点，无法做单元级映射核对。")

    check_hash(rep, a.source, "事实账本", a.ledger)
    check_hash(rep, a.source, "adapt-map", a.map)

    # 单元级多对多映射
    map_tables = read_tables(a.map)
    map_tbl = pick_table(map_tables, "MAP", "源单元集合", "目标单元集合")
    mapped_src, mapped_tgt = set(), set()
    if map_tbl is None:
        rep.block("M1", "adapt-map 里找不到带「MAP | 源单元集合 | 目标单元集合」的映射表。")
    else:
        for line, cells in map_tbl["rows"]:
            mid = plain(cell(map_tbl, cells, "MAP"))
            srcs = RE_UNIT_ID.findall(cell(map_tbl, cells, "源单元集合"))
            tgts = RE_UNIT_ID.findall(cell(map_tbl, cells, "目标单元集合"))
            if not srcs or not tgts:
                rep.block("M1", f"第 {line} 行：{mid} 的源单元或目标单元集合为空。")
            for s in srcs:
                (mapped_src.add(s) if s in src_units
                 else rep.block("M1", f"第 {line} 行：{mid} 引用的 {s} 在源文里不存在。"))
            for t in tgts:
                (mapped_tgt.add(t) if t in tgt_units
                 else rep.block("M1", f"第 {line} 行：{mid} 引用的 {t} 在目标稿里不存在。"))
        for s in sorted(src_units.keys() - mapped_src):
            rep.block("M1", f"源单元 {s} 没有出现在任何映射里（未映射，不能当作已覆盖）。")
        for t in sorted(tgt_units.keys() - mapped_tgt):
            rep.block("M1", f"目标单元 {t} 没有来源（凭空出现的段落）。")

    # 事实账本 → 事实落地表
    ledger_tbl = pick_table(read_tables(a.ledger), "FACT", "源单元")
    land_tbl = pick_table(map_tables, "FACT", "颗粒", "目标单元")
    if ledger_tbl is None:
        rep.block("M2", "事实账本里找不到带「FACT | 源单元」的表。")
    if land_tbl is None:
        rep.block("M2", "adapt-map 里找不到「事实落地表」（需要「FACT | 颗粒 | 源文值 | 目标单元 | 目标实现」）。"
                        "没有这张表就没有可机检的映射合同。")
    if ledger_tbl is None or land_tbl is None:
        return rep.emit(1)

    real_col = next((h for h in land_tbl["headers"] if h.startswith("目标实现")), "")
    ledger = {}
    for line, cells in ledger_tbl["rows"]:
        fid = plain(cell(ledger_tbl, cells, "FACT"))
        if not fid:
            continue
        ledger[fid] = {"line": line,
                       "src": plain(cell(ledger_tbl, cells, "源单元")),
                       "granules": {g: cell(ledger_tbl, cells, g).strip()
                                    for g in GRANULES if not unfilled(cell(ledger_tbl, cells, g))}}

    glossary = {}
    if a.glossary and Path(a.glossary).exists():
        g_tbl = pick_table(read_tables(a.glossary), "源语词", "目标语词")
        if g_tbl:
            for _, cells in g_tbl["rows"]:
                s, t = plain(cell(g_tbl, cells, "源语词")), plain(cell(g_tbl, cells, "目标语词"))
                if s and t:
                    glossary[s] = t
        rep.note(f"术语表 {a.glossary}：{len(glossary)} 条定译")
    else:
        rep.warn("M4", "未提供术语表，主体/对象的定译一致性这一层没有跑。")

    landed, declared = {}, []
    for line, cells in land_tbl["rows"]:
        fid = plain(cell(land_tbl, cells, "FACT"))
        gran = plain(cell(land_tbl, cells, "颗粒"))
        srcval = plain(cell(land_tbl, cells, "源文值"))
        tgt = plain(cell(land_tbl, cells, "目标单元"))
        real = cell(land_tbl, cells, real_col).strip()
        if not fid:
            continue
        if fid not in ledger:
            rep.block("M2", f"第 {line} 行：落地表写了 {fid}，事实账本里没有这一条。")
            continue
        if gran not in GRANULES:
            rep.block("M2", f"第 {line} 行：{fid} 的颗粒「{gran}」不是账本里的颗粒类别。")
            continue
        landed.setdefault((fid, gran), []).append(line)
        expect = ledger[fid]["granules"].get(gran, "")
        if not expect:
            rep.block("M2", f"第 {line} 行：{fid} 的「{gran}」在账本里是空的，落地表却声明了 {srcval}。"
                            "落地表不能反过来给账本添事实。")
        elif nfkc(plain(expect)) != nfkc(srcval):
            rep.block("M2", f"第 {line} 行：{fid}/{gran} 的源文值「{srcval}」与账本「{expect}」不一致。"
                            "账本是基准，改源文值等于绕过冻结。")
        if unfilled(real):
            rep.block("M3", f"第 {line} 行：{fid}/{gran} 没写目标实现，无法证明这个颗粒落地了。")
            continue
        declared.append(nfkc(real))
        if tgt not in tgt_units:
            rep.block("M3", f"第 {line} 行：{fid}/{gran} 指向的目标单元 {tgt or '（空）'} 在目标稿里不存在。")
            continue
        if nfkc(real) not in nfkc(tgt_units[tgt]):
            rep.block("M3", f"第 {line} 行：{fid}/{gran} 声明落在 {tgt} 的「{real}」在该单元正文里找不到。"
                            "合并/重排时这个颗粒被丢掉了，或者声明与成稿对不上。")
            continue
        if gran in IDENTITY_GRANULES:
            fixed = glossary.get(srcval)
            if fixed and nfkc(fixed) not in nfkc(real):
                rep.block("M4", f"第 {line} 行：{fid}/{gran}「{srcval}」的定译是「{fixed}」，"
                                f"目标实现写的是「{real}」。所指被换了。")
            elif not fixed and glossary and gran in GLOSSARY_REQUIRED:
                rep.block("M4", f"第 {line} 行：{fid}/{gran}「{srcval}」在术语表里没有定译，"
                                "主体一致性无法机检。先定译再走 adapt。")
            elif not fixed and glossary:
                rep.warn("M4", f"第 {line} 行：{fid}/{gran}「{srcval}」无定译，这一条只验证了落地，没验证所指。")

    for fid, info in ledger.items():
        for gran in info["granules"]:
            if (fid, gran) not in landed:
                rep.block("M2", f"账本第 {info['line']} 行：{fid} 的「{gran}」"
                                f"（{info['granules'][gran]}）在落地表里没有任何一行。映射缺口。")

    # 数字 / 日期 / URL：集合比较，天然适配 N≠M
    src_plain, tgt_plain = RE_COMMENT.sub("", src_text), RE_COMMENT.sub("", draft_text)
    src_facts, tgt_facts = fact_view(src_text), fact_view(draft_text)
    for name, extractor, s_in, t_in in (
            ("数字", lambda t: fact_check.extract_numbers(t, 12), src_facts, tgt_facts),
            ("日期", lambda t: fact_check.extract(fact_check.RE_DATE, t, 12), src_facts, tgt_facts),
            ("URL", lambda t: fact_check.extract(fact_check.RE_URL, t, 12), src_plain, tgt_plain),
            ("占位符", lambda t: fact_check.extract(fact_check.RE_PLACEHOLDER, t, 12), src_plain, tgt_plain)):
        s_items, t_items = extractor(s_in), extractor(t_in)
        only_src, only_tgt = fact_check.diff(s_items, t_items)
        for k, n in only_src.items():
            rep.block("M5", f"{name} `{k}` 只在源文出现 ×{n}：… {fact_check.first_ctx(s_items, k)}")
        for k, n in only_tgt.items():
            raws = {nfkc(i["raw"]) for i in t_items if i["key"] == k}
            if any(r in d for r in raws for d in declared):
                # 英语把小数目拼成词（two / three），日语写作数字——正则只抓阿拉伯数字，会误判成「加事实」。
                # 已在落地表声明为某个颗粒的目标实现时，降为需人工确认。
                rep.warn("M5", f"{name} `{k}` 只在目标稿出现 ×{n}，但已在落地表声明为某个颗粒的目标实现。"
                               "源语把数目拼成词、目标语写成数字属于正常；**换算、单位和位数请人工确认**。")
            else:
                rep.block("M5", f"{name} `{k}` 只在目标稿出现 ×{n}：… {fact_check.first_ctx(t_items, k)}"
                                "（adapt 不许加源文没有的事实；确需加入请先请作者改源文）")

    rep.note(f"事实账本：{len(ledger)} 条，"
             f"非空颗粒 {sum(len(v['granules']) for v in ledger.values())} 个；"
             f"落地表 {len(land_tbl['rows'])} 行")
    return rep.emit(1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("gate", help="A4 生成前：核授权与作者批准事件")
    g.add_argument("--authorization", required=True)
    g.add_argument("--structure", required=True)
    g.add_argument("--conventions", required=True)
    g.add_argument("--map")
    g.set_defaults(func=run_gate)

    m = sub.add_parser("map", help="A4 之后：核多对多映射与事实颗粒落地")
    m.add_argument("--source", required=True)
    m.add_argument("--ledger", required=True)
    m.add_argument("--map", required=True)
    m.add_argument("--draft", required=True)
    m.add_argument("--authorization", required=True)
    m.add_argument("--glossary")
    m.set_defaults(func=run_map)

    a = ap.parse_args()
    sys.exit(a.func(a))


if __name__ == "__main__":
    main()
