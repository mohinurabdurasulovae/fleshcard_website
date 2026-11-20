"""Text + metadata extraction for PDF, HTML, Markdown and LaTeX documents.

Every extractor returns an :class:`Extracted` object whose ``text`` is a normalised,
plain-ish text where mathematics is preserved as ``$…$`` / ``$$…$$`` (rendered with
KaTeX in the frontend) and ``**bold**`` marks emphasised / defined terms. ``sections``
hold character offsets into ``text`` so flashcards can point back to the exact passage.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Extracted:
    title: str = ""
    author: str = ""
    text: str = ""
    sections: list[dict] = field(default_factory=list)
    page_count: int = 0
    meta: dict = field(default_factory=dict)

    @property
    def word_count(self) -> int:
        return len(self.text.split())

    def summary(self, n: int = 320) -> str:
        for sec in self.sections:
            body = self.text[sec["start"]:sec["end"]]
            for para in body.split("\n\n"):
                p = para.strip()
                if len(p) > 80 and not p.startswith("$$"):
                    return (p[:n] + "…") if len(p) > n else p
        t = self.text.strip()
        return (t[:n] + "…") if len(t) > n else t


class _Builder:
    def __init__(self) -> None:
        self.parts: list[str] = []
        self.sections: list[dict] = []
        self.pos = 0

    def add(self, title: str, body: str, level: int = 1, page: int | None = None) -> None:
        body = _tidy(body)
        if not body:
            return
        if self.parts:
            self.parts.append("\n\n")
            self.pos += 2
        start = self.pos
        self.parts.append(body)
        self.pos += len(body)
        self.sections.append({"title": (title or "").strip()[:300] or "Untitled section",
                              "level": level, "page": page, "start": start, "end": self.pos})

    def build(self) -> tuple[str, list[dict]]:
        return "".join(self.parts), self.sections


def _tidy(s: str) -> str:
    s = s.replace("\r", "").replace("\u200b", "").replace("\ufeff", "")
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", s)
    s = re.sub(r"[ \t\u00a0]+", " ", s)
    s = re.sub(r" *\n *", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


# ======================================================================================
# PDF
# ======================================================================================
_HEADING_RE = re.compile(r"^(?:(?:chapter|lecture|section|part)\s+\d+[.:]?\s*|\d+(?:\.\d+)*\.?\s+)?[A-Z][\w ,:;'’()&/\-]{2,80}$", re.I)


def _pdf_page_to_text(raw: str) -> str:
    raw = raw.replace("\u00ad", "")
    raw = re.sub(r"(\w)-\n(\w)", r"\1\2", raw)
    raw = re.sub(r"[ \t]*[●○▪■◦§•][ \t]*", "\n• ", raw)
    lines = [ln.strip() for ln in raw.split("\n")]
    out: list[str] = []
    for ln in lines:
        if not ln:
            out.append("\n")
            continue
        if out and out[-1] not in ("\n",):
            prev = out[-1]
            bullet = re.match(r"^([•\-–*▪◦●]|\d+[.)]|[a-z][.)])\s", ln)
            if bullet or (re.search(r"[.!?:]$", prev) and len(prev) < 60) or len(prev) < 25:
                out.append("\n" + ln)
            else:
                out.append(" " + ln)
        else:
            out.append(ln)
    text = "".join(x if x != "\n" else "\n\n" for x in out)
    return text


def _page_heading(text: str) -> str:
    for ln in text.split("\n")[:8]:
        ln = ln.strip()
        if 3 <= len(ln) <= 80 and len(ln.split()) <= 10 and not ln.endswith((".", ",")) and _HEADING_RE.match(ln):
            if not re.fullmatch(r"[\d\s.]+", ln) and not re.match(r"^page\s*\d+", ln, re.I):
                return ln
    return ""


def extract_pdf(data: bytes) -> Extracted:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    ex = Extracted(page_count=len(reader.pages))
    try:
        info = reader.metadata or {}
        ex.title = str(info.get("/Title") or "").strip()
        ex.author = str(info.get("/Author") or "").strip()
    except Exception:
        pass
    b = _Builder()
    last_heading = ""
    for i, page in enumerate(reader.pages, start=1):
        try:
            raw = page.extract_text() or ""
        except Exception:
            raw = ""
        text = _pdf_page_to_text(raw)
        heading = _page_heading(text)
        if heading:
            last_heading = heading
        title = f"Page {i}" + (f" · {heading or last_heading}" if (heading or last_heading) else "")
        b.add(title, text, level=1, page=i)
    ex.text, ex.sections = b.build()
    if not ex.title and ex.sections:
        first = ex.text[: ex.sections[0]["end"]].strip().split("\n")[0]
        ex.title = first[:120]
    return ex


# ======================================================================================
# HTML
# ======================================================================================

def extract_html(data: bytes | str, base_title: str = "") -> Extracted:
    from bs4 import BeautifulSoup

    html = data.decode("utf-8", "replace") if isinstance(data, bytes) else data
    soup = BeautifulSoup(html, "lxml")
    ex = Extracted()
    if soup.title and soup.title.string:
        ex.title = soup.title.string.strip()
    meta_author = soup.find("meta", attrs={"name": "author"})
    if meta_author and meta_author.get("content"):
        ex.author = meta_author["content"].strip()

    # ---- preserve maths ----
    for ann in soup.select('annotation[encoding="application/x-tex"]'):
        tex = ann.get_text()
        container = ann.find_parent(class_="katex-display")
        katex = ann.find_parent(class_="katex")
        target = container or katex
        if target is not None:
            target.replace_with(f" $${tex}$$ " if container else f" ${tex}$ ")
    for sc in soup.select('script[type^="math/tex"]'):
        tex = sc.get_text()
        sc.replace_with(f" $${tex}$$ " if "display" in sc.get("type", "") else f" ${tex}$ ")
    for mj in soup.select(".MathJax, .MathJax_Preview, .MathJax_Display, mjx-container"):
        mj.decompose()

    for tag in soup(["script", "style", "noscript", "nav", "header", "footer", "aside", "form", "svg", "button", "iframe"]):
        tag.decompose()
    for sel in [".sidebar", ".toc", "#toc", ".navbar", ".menu", ".breadcrumb", ".pagination", ".post-meta", ".comments"]:
        for t in soup.select(sel):
            t.decompose()

    main = (soup.select_one("article") or soup.select_one("main") or soup.select_one("[role=main]")
            or soup.select_one(".content") or soup.select_one("#content") or soup.select_one(".post")
            or soup.body or soup)

    h1 = main.find("h1")
    if h1 and h1.get_text(strip=True):
        ex.title = h1.get_text(" ", strip=True)

    for b_ in main.find_all(["strong", "b"]):
        t = b_.get_text(" ", strip=True)
        if t and "$" not in t:
            b_.replace_with(f"**{t}**")
    for br in main.find_all("br"):
        br.replace_with("\n")
    for li in main.find_all("li"):
        li.insert_before("\n• ")
    for pre in main.find_all("pre"):
        pre.insert_before("\n\n")
        pre.insert_after("\n\n")
    for blk in main.find_all(["p", "div", "section", "table", "tr", "blockquote", "ul", "ol", "dd", "dt", "figure"]):
        blk.insert_after("\n\n")
    for h in main.find_all(["h1", "h2", "h3", "h4"]):
        level = int(h.name[1])
        h.replace_with(f"\n\n\x01H{level}\x02{h.get_text(' ', strip=True)}\x03\n\n")

    raw = main.get_text()
    b = _Builder()
    title, level = "Introduction", 1
    pos = 0
    for m in re.finditer(r"\x01H(\d)\x02(.*?)\x03", raw):
        b.add(title, raw[pos:m.start()], level)
        title, level = m.group(2), int(m.group(1))
        pos = m.end()
    b.add(title, raw[pos:], level)
    ex.text, ex.sections = b.build()
    if not ex.title:
        ex.title = base_title
    return ex


# ======================================================================================
# Markdown
# ======================================================================================

def extract_markdown(data: bytes | str) -> Extracted:
    md = data.decode("utf-8", "replace") if isinstance(data, bytes) else data
    md = md.replace("\r\n", "\n")
    md = re.sub(r"^---\n.*?\n---\n", "", md, flags=re.S)  # front matter
    # setext headings -> atx
    md = re.sub(r"^(.+)\n=+\s*$", r"# \1", md, flags=re.M)
    md = re.sub(r"^(.+)\n-{3,}\s*$", r"## \1", md, flags=re.M)
    md = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", md)
    md = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", md)
    md = re.sub(r"<[^>]+>", "", md)
    md = re.sub(r"^\s*[-*+]\s+", "• ", md, flags=re.M)
    md = re.sub(r"\\\[(.+?)\\\]", r"$$\1$$", md, flags=re.S)
    md = re.sub(r"\\\((.+?)\\\)", r"$\1$", md, flags=re.S)

    ex = Extracted()
    b = _Builder()
    title, level, buf = "Introduction", 1, []
    in_code = False
    for line in md.split("\n"):
        if line.strip().startswith("```"):
            in_code = not in_code
            buf.append(line)
            continue
        m = None if in_code else re.match(r"^(#{1,4})\s+(.+?)\s*#*\s*$", line)
        if m:
            if not ex.title and len(m.group(1)) == 1:
                ex.title = m.group(2)
            b.add(title, "\n".join(buf), level)
            title, level, buf = m.group(2), len(m.group(1)), []
        else:
            buf.append(line)
    b.add(title, "\n".join(buf), level)
    ex.text, ex.sections = b.build()
    return ex


# ======================================================================================
# LaTeX
# ======================================================================================
THEOREM_ENVS = {
    "definition": "Definition", "defn": "Definition", "defi": "Definition", "dfn": "Definition", "def": "Definition",
    "theorem": "Theorem", "thm": "Theorem", "lemma": "Lemma", "lem": "Lemma", "proposition": "Proposition",
    "prop": "Proposition", "corollary": "Corollary", "cor": "Corollary", "law": "Law", "postulate": "Postulate",
    "axiom": "Axiom", "claim": "Claim", "notation": "Notation", "example": "Example", "eg": "Example", "ex": "Example",
    "remark": "Remark", "rem": "Remark", "note": "Note", "exercise": "Exercise", "significant": "Key result",
    "principle": "Principle", "result": "Result", "conjecture": "Conjecture", "fact": "Fact",
}
DISPLAY_MATH_ENVS = ["equation", "align", "gather", "multline", "eqnarray", "displaymath", "flalign", "empheq", "alignat"]
DROP_ENVS = ["figure", "tikzpicture", "table", "subfigure", "subtable", "wrapfigure", "pgfonlayer", "scope",
             "thebibliography", "comment", "minted", "lstlisting", "verbatim", "titlepage", "tabular", "circuitikz", "axis"]


def _group(s: str, i: int, open_: str = "{", close: str = "}") -> int:
    """Given s[i] == open_, return index just after the matching close."""
    depth = 0
    j = i
    while j < len(s):
        c = s[j]
        if c == "\\":
            j += 2
            continue
        if c == open_:
            depth += 1
        elif c == close:
            depth -= 1
            if depth == 0:
                return j + 1
        j += 1
    return len(s)


def _strip_comments(src: str) -> str:
    return re.sub(r"(?<!\\)%.*", "", src)


def _resolve_inputs(src: str, base: Path, root: Path | None, depth: int = 0) -> str:
    if depth > 6:
        return src

    def repl(m: re.Match) -> str:
        name = m.group(2).strip()
        if m.group(1) == "import":
            return m.group(0)
        for cand_base in [base, root] if root else [base]:
            if cand_base is None:
                continue
            for cand in (cand_base / name, cand_base / f"{name}.tex"):
                if cand.is_file():
                    try:
                        sub = _strip_comments(cand.read_text("utf-8", "replace"))
                    except Exception:
                        return ""
                    sub = re.sub(r"^.*?\\begin\{document\}", "", sub, flags=re.S) if "\\begin{document}" in sub else sub
                    sub = sub.replace("\\end{document}", "")
                    return _resolve_inputs(sub, cand.parent, root, depth + 1)
        return ""

    src = re.sub(r"\\(input|include|subfile|subimport\{[^}]*\}|import)\s*\{([^}]+)\}", repl, src)
    return src


def _extract_macros(src: str) -> dict:
    macros: dict[str, str] = {}
    for m in re.finditer(r"\\(?:re|provide)?newcommand\*?\s*\{?\\([A-Za-z]+)\}?\s*(?:\[(\d)\])?\s*(?:\[[^\]]*\])?\s*\{", src):
        end = _group(src, m.end() - 1)
        body = src[m.end():end - 1]
        if len(body) < 300:
            macros["\\" + m.group(1)] = body
    for m in re.finditer(r"\\def\s*\\([A-Za-z]+)\s*\{", src):
        end = _group(src, m.end() - 1)
        macros.setdefault("\\" + m.group(1), src[m.end():end - 1])
    for m in re.finditer(r"\\DeclareMathOperator\*?\s*\{\\([A-Za-z]+)\}\s*\{([^}]*)\}", src):
        macros["\\" + m.group(1)] = "\\operatorname{" + m.group(2) + "}"
    return macros


def _brace_arg(src: str, cmd: str) -> str:
    m = re.search(r"\\" + cmd + r"\s*(?:\[[^\]]*\])?\s*\{", src)
    if not m:
        return ""
    end = _group(src, m.end() - 1)
    return src[m.end():end - 1]


def _replace_cmd(s: str, names: str, fmt) -> str:
    pat = re.compile(r"\\(" + names + r")\*?\s*\{")
    out = []
    pos = 0
    while True:
        m = pat.search(s, pos)
        if not m:
            break
        end = _group(s, m.end() - 1)
        out.append(s[pos:m.start()])
        out.append(fmt(m.group(1), s[m.end():end - 1]))
        pos = end
    out.append(s[pos:])
    return "".join(out)


def latex_to_text(src: str) -> tuple[str, list[tuple[str, int, int]]]:
    """Return (text, markers) where markers are (title, level, offset) for sectioning."""
    s = src
    # drop environments entirely
    for env in DROP_ENVS:
        s = re.sub(r"\\begin\{" + env + r"\*?\}.*?\\end\{" + env + r"\*?\}", "\n", s, flags=re.S)

    # ---- protect maths ----
    maths: list[str] = []

    def keep(tex: str, display: bool) -> str:
        tex = re.sub(r"\\(label|nonumber|notag|tag)\s*(\{[^}]*\})?", "", tex).strip()
        maths.append(f"$${tex}$$" if display else f"${tex}$")
        return f"\x00{len(maths) - 1}\x00" if not display else f"\n\n\x00{len(maths) - 1}\x00\n\n"

    for env in DISPLAY_MATH_ENVS:
        def env_repl(m: re.Match, env=env) -> str:
            body = m.group(1)
            if env in ("align", "eqnarray", "flalign", "alignat", "empheq"):
                body = re.sub(r"^\s*(\{[^}]*\}|\[[^\]]*\])", "", body)
                body = "\\begin{aligned}" + body + "\\end{aligned}"
            elif env in ("gather", "multline"):
                body = "\\begin{gathered}" + body + "\\end{gathered}"
            return keep(body, True)
        s = re.sub(r"\\begin\{" + env + r"\*?\}(.*?)\\end\{" + env + r"\*?\}", env_repl, s, flags=re.S)
    s = re.sub(r"\$\$(.+?)\$\$", lambda m: keep(m.group(1), True), s, flags=re.S)
    s = re.sub(r"\\\[(.+?)\\\]", lambda m: keep(m.group(1), True), s, flags=re.S)
    s = re.sub(r"\\\((.+?)\\\)", lambda m: keep(m.group(1), False), s, flags=re.S)
    s = re.sub(r"(?<!\\)\$(.+?)(?<!\\)\$", lambda m: keep(m.group(1), False), s, flags=re.S)

    # ---- theorem-like environments ----
    def thm_repl(m: re.Match) -> str:
        env = m.group(1)
        label = THEOREM_ENVS[env.lower()]
        rest = m.group(2)
        name = ""
        mm = re.match(r"\s*\[([^\]]*)\]", rest)
        if mm:
            name = mm.group(1)
            rest = rest[mm.end():]
        elif rest.lstrip().startswith("{") and env.lower() not in ("theorem", "definition"):
            k = rest.index("{")
            end = _group(rest, k)
            name = rest[k + 1:end - 1]
            rest = rest[end:]
        head = f"**{label}**" + (f" ({name.strip()})" if name.strip() else "") + "."
        return f"\n\n{head} {rest.strip()}\n\n"

    env_names = "|".join(sorted(THEOREM_ENVS, key=len, reverse=True))
    for _ in range(2):
        s = re.sub(r"\\begin\{(" + env_names + r")\*?\}(.*?)\\end\{\1\*?\}", thm_repl, s, flags=re.S | re.I)
    s = re.sub(r"\\begin\{proof\}(\[[^\]]*\])?", "\n\n*Proof.* ", s)
    s = s.replace("\\end{proof}", " ∎\n\n")

    # lists
    s = re.sub(r"\\item\s*\[([^\]]*)\]", r"\n• **\1** ", s)
    s = re.sub(r"\\item\b", "\n• ", s)
    s = re.sub(r"\\begin\{(itemize|enumerate|description|center|flushleft|flushright|quote|quotation|minipage|abstract)\}(\[[^\]]*\]|\{[^}]*\})*", "\n", s)
    s = re.sub(r"\\end\{(itemize|enumerate|description|center|flushleft|flushright|quote|quotation|minipage|abstract)\}", "\n", s)

    # sectioning markers
    markers_tmp: list[tuple[str, int]] = []
    levels = {"part": 0, "chapter": 1, "section": 1, "subsection": 2, "subsubsection": 3}

    out = []
    pos = 0
    for m in re.finditer(r"\\(part|chapter|section|subsection|subsubsection)\*?\s*(?:\[[^\]]*\])?\s*\{", s):
        if m.start() < pos:
            continue
        end = _group(s, m.end() - 1)
        title = s[m.end():end - 1]
        out.append(s[pos:m.start()])
        markers_tmp.append((title, levels[m.group(1)]))
        out.append(f"\n\n\x01S{len(markers_tmp) - 1}\x01\n\n")
        pos = end
    out.append(s[pos:])
    s = "".join(out)
    s = _replace_cmd(s, "paragraph|subparagraph", lambda c, a: f"\n\n**{a}** ")

    # formatting
    s = _replace_cmd(s, "textbf|emph|textit|textsl|underline|keyword|term|defined|vocab|important",
                     lambda c, a: f"**{a}**")
    s = _replace_cmd(s, "href", lambda c, a: "")
    s = _replace_cmd(s, "footnote|index|label|ref|eqref|cref|Cref|cite|citep|citet|pageref|hyperref|vspace|hspace|"
                        "includegraphics|caption|bibliography|bibliographystyle|addcontentsline|setcounter|addtocounter|"
                        "newcommand|renewcommand|usepackage|documentclass|marginpar|todo|thispagestyle|pagestyle|"
                        "input|graphicspath|hypersetup|lecture|nocite|qedhere",
                     lambda c, a: "")
    for _ in range(3):
        s = _replace_cmd(s, r"[A-Za-z]+", lambda c, a: a)
    s = re.sub(r"\\(maketitle|tableofcontents|newpage|clearpage|noindent|centering|par|bigskip|medskip|smallskip|"
               r"hfill|vfill|linebreak|pagebreak|appendix|printindex|qed|indent|small|large|Large|footnotesize|"
               r"normalsize|bfseries|itshape|item)\b", "\n", s)
    s = re.sub(r"\\\\(\[[^\]]*\])?", "\n", s)
    s = re.sub(r"\\[A-Za-z]+\*?(\[[^\]]*\])?", "", s)
    s = s.replace("~", " ").replace("``", "“").replace("''", "”").replace("---", "—").replace("--", "–")
    s = re.sub(r"\\([&%$#_{}])", r"\1", s)
    s = re.sub(r"(?<!\\)[{}]", "", s)

    # restore maths (placeholders can be nested when maths contains maths)
    def restore(x: str) -> str:
        for _ in range(4):
            if "\x00" not in x:
                break
            x = re.sub(r"\x00(\d+)\x00", lambda m: maths[int(m.group(1))], x)
        return x.replace("\x00", "")

    s = restore(s)

    # split into marker offsets
    markers: list[tuple[str, int, int]] = []
    clean_parts = []
    pos = 0
    offset = 0
    for m in re.finditer(r"\x01S(\d+)\x01", s):
        chunk = s[pos:m.start()]
        clean_parts.append(chunk)
        offset += len(chunk)
        title, lvl = markers_tmp[int(m.group(1))]
        title = latex_inline_to_text(restore(title))
        markers.append((title, lvl, offset))
        pos = m.end()
    clean_parts.append(s[pos:])
    return "".join(clean_parts), markers


def latex_inline_to_text(t: str) -> str:
    t = re.sub(r"\\(texorpdfstring)\s*\{([^}]*)\}\s*\{([^}]*)\}", r"\3", t)
    for _ in range(2):
        t = _replace_cmd(t, r"[A-Za-z]+", lambda c, a: a)
    t = re.sub(r"\\[A-Za-z]+", "", t).replace("{", "").replace("}", "")
    return re.sub(r"\s+", " ", t).strip()


def _latex_title(raw: str, macros: dict) -> str:
    for _ in range(3):
        for name, body in macros.items():
            if "#" not in body and name in raw:
                raw = re.sub(re.escape(name) + r"(?![A-Za-z])(\{\})?", lambda m: body, raw)
    for part in re.split(r"\\\\|\\newline", raw):
        t = latex_inline_to_text(part).strip(" -–—,:")
        if len(re.findall(r"[A-Za-z]", t)) >= 4 and not re.search(r"lectures? by|notes taken|^part [ivx]+$|report typos", t, re.I):
            return t
    return ""


def extract_latex(data: bytes | str, path: Path | None = None, root: Path | None = None) -> Extracted:
    src = data.decode("utf-8", "replace") if isinstance(data, bytes) else data
    src = _strip_comments(src)
    base = path.parent if path else Path(".")
    src = _resolve_inputs(src, base, root)
    # header files referenced via \input in the preamble have been inlined above
    preamble, _, body = src.partition("\\begin{document}")
    if not body:
        body, preamble = preamble, ""
    body = body.split("\\end{document}")[0]

    ex = Extracted()
    ex.meta["katex_macros"] = _extract_macros(preamble or src)
    ex.title = _latex_title(_brace_arg(preamble or src, "title"), ex.meta["katex_macros"])
    ex.author = latex_inline_to_text(_brace_arg(preamble or src, "author")).replace("\\and", ",")
    ex.meta["katex_macros"] = _extract_macros(preamble or src)

    text, markers = latex_to_text(body)
    b = _Builder()
    prev_title, prev_level, prev_off = "Introduction", 1, 0
    for title, lvl, off in markers:
        b.add(prev_title, text[prev_off:off], prev_level)
        prev_title, prev_level, prev_off = title, lvl, off
    b.add(prev_title, text[prev_off:], prev_level)
    ex.text, ex.sections = b.build()
    return ex


def detect_format(name: str, content_type: str = "", data: bytes | None = None) -> str:
    n = name.lower().split("?")[0]
    if n.endswith(".pdf") or "pdf" in content_type or (data or b"")[:5] == b"%PDF-":
        return "pdf"
    if n.endswith((".md", ".markdown")):
        return "md"
    if n.endswith(".tex"):
        return "tex"
    return "html"


def extract(data: bytes, fmt: str, path: Path | None = None, root: Path | None = None, title: str = "") -> Extracted:
    if fmt == "pdf":
        return extract_pdf(data)
    if fmt == "md":
        return extract_markdown(data)
    if fmt == "tex":
        return extract_latex(data, path, root)
    return extract_html(data, base_title=title)
