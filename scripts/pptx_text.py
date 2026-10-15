#!/usr/bin/env python3
"""pptx_text.py — 从 .pptx 按幻灯片顺序抽取文字（stdlib only，不改原文件）。

用法: python3 pptx_text.py <file.pptx> [--notes] > out.md
输出 markdown：每页一个 "## Slide N" 标题，每个形状/表格之间空一行，每个段落一行。
"""
import re
import sys
import zipfile
from xml.etree import ElementTree as ET

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def slide_order(z):
    pres = ET.fromstring(z.read("ppt/presentation.xml"))
    rels = ET.fromstring(z.read("ppt/_rels/presentation.xml.rels"))
    rid2target = {r.get("Id"): r.get("Target") for r in rels.findall("rel:Relationship", NS)}
    order = []
    for sld in pres.findall(".//p:sldIdLst/p:sldId", NS):
        rid = sld.get("{%s}id" % NS["r"])
        target = rid2target.get(rid, "")
        if target:
            order.append("ppt/" + target.lstrip("/").replace("ppt/", "", 1) if not target.startswith("ppt/") else target)
    return order


def paragraphs(elem):
    out = []
    for p in elem.iter("{%s}p" % NS["a"]):
        texts = []
        for node in p.iter():
            tag = node.tag.split("}")[-1]
            if tag == "t" and node.text:
                texts.append(node.text)
            elif tag == "br":
                texts.append("\n")
        line = "".join(texts).strip()
        if line:
            out.append(line)
    return out


def shapes_text(root):
    blocks = []
    spTree = root.find(".//p:cSld/p:spTree", NS)
    if spTree is None:
        return blocks
    for child in spTree:
        tag = child.tag.split("}")[-1]
        if tag in ("sp", "graphicFrame", "grpSp"):
            paras = paragraphs(child)
            if paras:
                blocks.append(paras)
    return blocks


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(2)
    path = sys.argv[1]
    want_notes = "--notes" in sys.argv
    z = zipfile.ZipFile(path)
    names = set(z.namelist())
    order = slide_order(z)
    if not order:
        order = sorted([n for n in names if re.match(r"ppt/slides/slide\d+\.xml$", n)], key=lambda s: int(re.search(r"\d+", s).group()))
    print(f"# {path.split('/')[-1]}\n")
    for i, name in enumerate(order, 1):
        if name not in names:
            print(f"## Slide {i}\n（缺失 {name}）\n"); continue
        root = ET.fromstring(z.read(name))
        print(f"## Slide {i}\n")
        for block in shapes_text(root):
            for line in block:
                print(line)
            print()
        if want_notes:
            m = re.search(r"slide(\d+)\.xml$", name)
            nn = f"ppt/notesSlides/notesSlide{m.group(1)}.xml" if m else ""
            if nn in names:
                notes = paragraphs(ET.fromstring(z.read(nn)))
                if notes:
                    print("（备注）"); print("\n".join(notes)); print()


if __name__ == "__main__":
    main()
