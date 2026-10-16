#!/usr/bin/env python3
"""feedback_check.py — 反馈包的脱敏闸：提交前确认没把用户材料带出去。

用法: python3 feedback_check.py <feedback-pack.md> --against <源文> [<译文> ...] [--max-run 15]

查三件事，任何一项命中即退出码 1：
  1. 与 --against 文件共有的连续片段 ≥ --max-run 字（忽略空白）——原文整句被抄进反馈包
  2. 邮箱、网址（本 skill 仓库地址与 example.com/org/net 除外）、本机路径
  3. 读不到文件或文件为空 → 退出码 2（"什么都没比对"不能当通过）
另列出 ≥4 位的数字和带货币的金额供人工确认（只提示，不影响退出码）。
stdlib only。输出 markdown。
"""
import argparse
import re
import sys
from pathlib import Path

ALLOWED_URL = re.compile(r"https?://(?:www\.)?(?:github\.com/TunaSaiko/localize\S*|example\.(?:com|org|net)\S*)")
RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
RE_URL = re.compile(r"https?://[^\s<>\"'）)】\]|]+|www\.[^\s<>\"'）)】\]|]+")
RE_PATH = re.compile(r"(?:/Users/|/home/|~/|[A-Za-z]:\\)[^\s|`]*")
RE_BIGNUM = re.compile(r"(?:[¥￥$€£]\s?\d[\d,，.]*|\d[\d,，.]*\s?(?:万|亿|億|円|元|ドル|美元)|\d{4,})")
WS = re.compile(r"\s+")


def squash(text):
    """去掉全部空白，返回 (压缩后文本, 每个字符在原文中的位置)。"""
    chars, pos = [], []
    for i, ch in enumerate(text):
        if not WS.match(ch):
            chars.append(ch)
            pos.append(i)
    return "".join(chars), pos


def shared_runs(pack, other, n):
    """pack 中与 other 共有、长度 ≥ n 的连续片段（按压缩后文本计），返回 [(start, end)] 原文区间。"""
    p, ppos = squash(pack)
    o, _ = squash(other)
    if len(p) < n or len(o) < n:
        return []
    grams = {o[i:i + n] for i in range(len(o) - n + 1)}
    hit = [False] * len(p)
    for i in range(len(p) - n + 1):
        if p[i:i + n] in grams:
            for j in range(i, i + n):
                hit[j] = True
    runs, i = [], 0
    while i < len(p):
        if hit[i]:
            j = i
            while j < len(p) and hit[j]:
                j += 1
            runs.append((ppos[i], ppos[j - 1] + 1))
            i = j
        else:
            i += 1
    return runs


def read(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"错误：读不到 {path}（{exc}）", file=sys.stderr)
        sys.exit(2)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pack")
    ap.add_argument("--against", nargs="+", required=True, help="源文、译文等用户材料")
    ap.add_argument("--max-run", type=int, default=15, help="与材料共有的连续字数上限（默认 15）")
    args = ap.parse_args()

    pack = read(args.pack)
    if not pack.strip():
        print(f"错误：{args.pack} 是空文件，没有可检查的内容", file=sys.stderr)
        sys.exit(2)
    others = []
    for path in args.against:
        text = read(path)
        if not text.strip():
            print(f"错误：{path} 是空文件——没有比对对象就不能判定脱敏", file=sys.stderr)
            sys.exit(2)
        others.append((path, text))

    print("# feedback_check 报告\n")
    print(f"反馈包: {args.pack}（{len(squash(pack)[0])} 字，不计空白）")
    for path, text in others:
        print(f"比对: {path}（{len(squash(text)[0])} 字）")
    print(f"阈值: 共有连续片段 ≥ {args.max_run} 字即报\n")

    fail = 0
    print("## 1. 与用户材料共有的长片段")
    found = False
    for path, text in others:
        for a, b in shared_runs(pack, text, args.max_run):
            found = True
            fail += 1
            print(f"- 与 `{path}` 共有：`{pack[a:b].strip()}`")
    if not found:
        print("- 无。")

    print("\n## 2. 邮箱 / 网址 / 本机路径")
    items = [("邮箱", m.group()) for m in RE_EMAIL.finditer(pack)]
    items += [("网址", m.group()) for m in RE_URL.finditer(pack) if not ALLOWED_URL.match(m.group())]
    items += [("路径", m.group()) for m in RE_PATH.finditer(pack)]
    for kind, value in items:
        fail += 1
        print(f"- {kind}：`{value}`")
    if not items:
        print("- 无。")

    print("\n## 3. 需要人工确认的数字（只提示）")
    nums = sorted({m.group().strip() for m in RE_BIGNUM.finditer(pack)})
    print("\n".join(f"- `{n}`：是否来自用户材料？是就换成 `<数字>`" for n in nums) if nums else "- 无。")

    print(f"\n## 汇总\n- 必须处理: {fail} 项")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
