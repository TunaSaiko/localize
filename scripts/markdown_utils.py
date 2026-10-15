"""Bounded Markdown views for linting, not a CommonMark renderer."""
import re
from pathlib import Path

INLINE_CODE = re.compile(r"(?<!`)(`+)(?!`)(.*?)\1(?!`)", re.S)
EMPHASIS = re.compile(
    r"(?<![\\*])(?P<strong>\*\*)(?=\S)(.+?)(?<=\S)(?P=strong)(?!\*)"
    r"|(?<![\w\\_])(?P<under>__)(?=\S)(.+?)(?<=\S)(?P=under)(?![\w_])"
    r"|(?<![\\*])(?P<em>\*)(?=\S)(.+?)(?<=\S)(?P=em)(?!\*)"
    r"|(?<![\w\\_])(?P<single>_)(?=\S)(.+?)(?<=\S)(?P=single)(?![\w_])",
    re.S,
)


def _escaped(text, index):
    j = index - 1
    while j >= 0 and text[j] == "\\":
        j -= 1
    return (index - j - 1) % 2 == 1


def split_cells(line):
    text = line.strip()
    code_spans = [(m.start(), m.end()) for m in INLINE_CODE.finditer(text)]
    cuts = [i for i, ch in enumerate(text) if ch == "|" and not _escaped(text, i)
            and not any(a <= i < b for a, b in code_spans)]
    bounds = [-1] + cuts + [len(text)]
    cells = [text[a + 1:b].strip() for a, b in zip(bounds, bounds[1:])]
    if cuts and cuts[0] == 0:
        cells.pop(0)
    if cuts and cuts[-1] == len(text) - 1:
        cells.pop()
    return [cell.replace(r"\|", "|") for cell in cells]


def is_separator(line):
    if not line.lstrip().startswith("|"):
        return False
    cells = split_cells(line)
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", c) for c in cells)


def table_rows(path):
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    fence = None
    for i, line in enumerate(lines):
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence) and not line[marker.end():].strip():
                fence = None
            continue
        if fence or not line.lstrip().startswith("|") or is_separator(line):
            continue
        if i + 1 < len(lines) and is_separator(lines[i + 1]):
            continue
        yield i + 1, split_cells(line)


def _closing(text, start, opening, closing):
    depth = 0
    for i in range(start, len(text)):
        if _escaped(text, i):
            continue
        if text[i] == opening:
            depth += 1
        elif text[i] == closing:
            depth -= 1
            if depth == 0:
                return i
    return None


def link_labels(text):
    out = []
    i = 0
    while i < len(text):
        image = text.startswith("![", i)
        start = i + 1 if image else i
        if text[start:start + 1] == "[" and not _escaped(text, i):
            end = _closing(text, start, "[", "]")
            if end is not None and text[end + 1:end + 2] == "(":
                target_end = _closing(text, end + 1, "(", ")")
                if target_end is not None:
                    out.append(link_labels(text[start + 1:end]))
                    i = target_end + 1
                    continue
        out.append(text[i])
        i += 1
    return "".join(out)


def without_code(text):
    return INLINE_CODE.sub(" ", text)


def _url_punctuation(match):
    raw = match.group()
    end = len(raw.rstrip('.,;!?。！？'))
    return " " + raw[end:]


def prose_view(text):
    text = link_labels(without_code(text))
    text = re.sub(r"<https?://[^>]*>", " ", text)
    text = re.sub(r"https?://[^\s<>]+", _url_punctuation, text)
    text = re.sub(r"</?[A-Za-z][^>]*>", "", text)
    text = re.sub(r"^\s*(?:#{1,6}\s+|>\s*|[-*+]\s+|\d+[.)]\s+)", "", text, flags=re.M)
    text = EMPHASIS.sub(lambda m: next(m.group(i) for i in (2, 4, 6, 8) if m.group(i) is not None), text)
    return text.strip()


def emphasis_signature(text):
    text = link_labels(without_code(text))
    return tuple(sorted(m.group('strong') or m.group('under') or m.group('em') or m.group('single')
                        for m in EMPHASIS.finditer(text)))
