"""Rule-based flashcard generation (no API key needed).

Produces five card types — definition, concept, explanation, formula and comparison — and
records for every card the exact character span of the passage it came from, so students
can jump straight to that part of the lecture notes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

MATH_RE = re.compile(r"\$\$.+?\$\$|\$[^$\n]+?\$", re.S)
BOLD_RE = re.compile(r"\*\*([^*\n]{2,80})\*\*")
LABELS = "Definition|Theorem|Lemma|Proposition|Law|Postulate|Principle|Key result|Corollary|Axiom|Result|Fact|Notation"
BLOCK_RE = re.compile(r"\*\*(" + LABELS + r")\*\*(?: \(([^)\n]{1,90})\))?\.\s*")
PRONOUNS = {"this", "it", "these", "that", "there", "here", "we", "one", "they", "he", "she", "which", "what", "such",
            "each", "every", "some", "another", "our", "its", "his", "her", "if", "when", "so", "now", "then", "note",
            "thus", "hence", "also", "however", "i", "you", "all", "both", "any", "first", "last", "next"}
BAD_TERMS = {"example", "note", "proof", "answer", "solution", "remember", "ex", "q", "a", "step", "problem", "lecture",
             "chapter", "page", "topics", "goal", "reading", "warning", "hint", "aside", "idea", "recall", "claim",
             "question", "result", "case", "e.g", "i.e", "important", "key", "summary", "today", "announcements", "date"}
GENERIC_TITLES = {"introduction", "untitled section", "summary", "overview", "conclusion", "notation", "examples",
                  "exercises", "problems", "appendix", "references", "contents", "recap", "review", "admin", "logistics"}
GENERIC_ADJ = {"key", "main", "same", "following", "above", "other", "former", "latter", "second", "previous",
               "only", "general", "basic", "whole", "big", "important", "real", "obvious", "simplest", "best", "worst",
               "problem", "idea", "point", "goal", "answer", "trick", "catch", "issue", "upshot", "reason", "result"}
AUX = r"(is|are|was|were|can|cannot|can't|does|do|did|will|must|should|has|have|had|would|could)"


@dataclass
class Card:
    card_type: str
    question: str
    answer: str
    start: int
    end: int
    section_index: int
    confidence: float

    def key(self) -> str:
        return re.sub(r"[^a-z0-9]+", "", self.question.lower())[:120]


def clean(s: str) -> str:
    s = re.sub(r"\s*\n\s*(?=•)", "\n", s)
    parts = MATH_RE.split(s)
    maths = MATH_RE.findall(s)
    out = []
    for i, p in enumerate(parts):
        out.append(re.sub(r"[ \t]*\n[ \t]*(?!•)", " ", p))
        if i < len(maths):
            out.append(maths[i])
    return re.sub(r"[ \t]{2,}", " ", "".join(out)).strip()


def plain(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("**", "").replace("“", "").replace("”", "").replace('"', "")).strip()


def _mask(s: str) -> str:
    return MATH_RE.sub(lambda m: "M" * len(m.group()), s)


def sentence_spans(text: str, start: int, end: int) -> list[tuple[int, int]]:
    body = text[start:end]
    masked = _mask(body)
    spans = []
    for pm in re.finditer(r"(?:(?!\n\s*\n).)+", masked, re.S):
        p_start, para = pm.start(), pm.group()
        cuts = [0]
        for m in re.finditer(r"(?<=[.!?])[\"”’)]?\s+(?=[A-Z“\"(*•M\\])|\n(?=\s*•)", para):
            cuts.append(m.end())
        cuts.append(len(para))
        for a, b in zip(cuts, cuts[1:]):
            seg = para[a:b]
            lead = len(seg) - len(seg.lstrip())
            trail = len(seg.rstrip())
            if trail - lead > 3:
                spans.append((start + p_start + a + lead, start + p_start + a + trail))
    return spans


def _np(clause: str, max_words: int = 7) -> str:
    words = plain(clause).split()
    out = []
    for w in words:
        if re.fullmatch(AUX, w.lower()) or w.lower() in {"has", "uses", "requires", "allows", "provides", "takes",
                                                        "gives", "means", "makes", "needs", "runs", "stores"}:
            break
        out.append(w)
        if len(out) >= max_words:
            return ""
    return " ".join(out).strip(",;: ")


def _why(clause: str) -> str | None:
    c = plain(clause).rstrip(",;:. ").lstrip("• ")
    c = re.sub(r"^(?:Note|Recall|Remember|Observe|Notice|So|And|But|Also|Now)(?: that)?,?\s+", "", c, flags=re.I)
    if len(c) < 12 or c.lower().startswith(("it ", "this ", "that ", "we ", "they ", "there ")):
        return None
    m = re.match(r"^(?:(The|This|An?|Our|These|Those)\s+)?(.{2,80}?)\s+" + AUX + r"\s+(not\s+)?(.+)$", c, re.I)
    if not m:
        return None
    det, subj, aux, neg, rest = m.groups()
    if (det or "").lower() == "this" or subj.lower() in PRONOUNS:
        return None
    if any(w.lower().strip(",") in {"we", "you", "i", "it", "they", "this", "that", "there", "later", "here", "now"}
           for w in subj.split()) or len(subj.split()) > 8:
        return None
    subj = (f"{det.lower()} " if det else "") + (subj if subj[:2].isupper() else subj[0].lower() + subj[1:])
    if aux.lower() in ("cannot", "can't"):
        return f"Why can't {subj} {rest}?"
    return f"Why {aux.lower()} {subj} {(neg or '')}{rest}?".replace("  ", " ")


def _ok_term(term: str) -> bool:
    t = plain(term).strip(" .,:;")
    if not (2 <= len(t) <= 70) or len(t.split()) > 7:
        return False
    first = t.split()[0].lower()
    if any(w.lower().endswith("ly") and len(w) > 4 for w in t.split()[1:]):
        return False
    if first in GENERIC_ADJ:
        return False
    return first not in PRONOUNS and t.lower() not in BAD_TERMS and not re.fullmatch(r"[\d\W]+", t)


class Generator:
    def __init__(self, text: str, sections: list[dict], max_cards: int = 40):
        self.text = text
        self.sections = sections or [{"title": "", "start": 0, "end": len(text), "page": None}]
        self.max_cards = max_cards
        self.cards: list[Card] = []
        self.used: list[tuple[int, int]] = []

    # ---------------------------------------------------------------- helpers
    def _overlaps(self, a: int, b: int) -> bool:
        return any(a < y and x < b for x, y in self.used)

    def add(self, card_type, q, ans, start, end, si, conf):
        ans = clean(ans)
        q = re.sub(r"\s+", " ", q).strip()
        if not (15 <= len(ans) <= 1100) or len(q) > 260 or len(q) < 8:
            return
        if self._overlaps(start, end) and card_type != "formula":
            return
        self.used.append((start, end))
        self.cards.append(Card(card_type, q, ans, start, end, si, conf))

    # ---------------------------------------------------------------- rules
    def theorem_blocks(self, si: int, s: dict) -> None:
        body_start, body_end = s["start"], s["end"]
        for m in BLOCK_RE.finditer(self.text, body_start, body_end):
            label, name = m.group(1), (m.group(2) or "").strip()
            # block: following paragraphs while they are maths or continuation lines
            pos = m.end()
            end = self.text.find("\n\n", pos)
            end = body_end if end == -1 or end > body_end else end
            while end < body_end:
                nxt_start = end + 2
                nxt_end = self.text.find("\n\n", nxt_start)
                nxt_end = body_end if nxt_end == -1 or nxt_end > body_end else nxt_end
                nxt = self.text[nxt_start:nxt_end].lstrip()
                prev = self.text[pos:end].rstrip()
                if nxt.startswith("$$") or (prev.endswith("$$") and nxt[:1].islower()) or prev.endswith(":"):
                    end = nxt_end
                else:
                    break
                if end - pos > 900:
                    break
            body = self.text[pos:end].strip()
            if len(plain(body)) < 20:
                continue
            title = s.get("title", "")
            if label == "Definition" or label == "Notation":
                bolds = [b for b in BOLD_RE.findall(body) if _ok_term(b)]
                term = name or (bolds[0] if bolds else "")
                if term and _ok_term(term):
                    q = f"What is the definition of {plain(term)}?"
                    conf = 0.85
                elif bolds:
                    q = f"Define: {plain(bolds[0])}"
                    conf = 0.7
                else:
                    q = f"State the definition introduced in “{title}”."
                    conf = 0.45
                self.add("definition", q, body, m.start(), end, si, conf)
            else:
                if name:
                    low = name.lower()
                    if any(w in low for w in ("theorem", "law", "principle", "lemma", "equation", "rule", "postulate", "formula")):
                        q = f"State {'the ' if not low.startswith('the ') else ''}{plain(name)}."
                    else:
                        q = f"State the {label.lower()} about {plain(name)}."
                    conf = 0.8
                else:
                    q = f"State the {label.lower()} given in “{title}”." if title and title.lower() not in GENERIC_TITLES else None
                    conf = 0.5
                if q:
                    ctype = "formula" if label in ("Law", "Postulate") and "$$" in body and len(body) < 400 else "concept"
                    self.add(ctype, q, body, m.start(), end, si, conf)

    def sentence_rules(self, si: int, s: dict) -> None:
        spans = sentence_spans(self.text, s["start"], s["end"])
        for k, (a, b) in enumerate(spans):
            raw = self.text[a:b]
            sent = clean(raw)
            ps = plain(sent).lstrip("• ")
            nwords = len(ps.split())
            if nwords < 6 or nwords > 70:
                continue
            nxt = spans[k + 1] if k + 1 < len(spans) else None
            ext_b = nxt[1] if nxt and (sent.endswith(":") or len(plain(self.text[nxt[0]:nxt[1]])) < 80) else b
            body_ext = self.text[a:ext_b]

            # ---- definitions with a bold term
            m = re.match(r"^•?\s*(?:An?|The)?\s*\*\*([^*]{2,70})\*\*\s*(?:\([^)]*\)\s*)?,?\s*(?:\w+ly\s+)?(is|are|refers to|refer to|means|denotes|describes)\b", sent)
            if not m:
                m = re.search(r"\b(?:called|known as|termed|we call|we define|define)\s+(?:an?|the)?\s*\*\*([^*]{2,70})\*\*", sent)
            if m and _ok_term(m.group(1)):
                term = plain(m.group(1))
                plural = m.lastindex and m.lastindex >= 2 and m.group(2) in ("are", "refer to")
                self.add("definition", f"What {'are' if plural else 'is'} {'an' if not plural and term[0].lower() in 'aeiou' else 'a' if not plural else ''} {term}?".replace("  ", " ")
                         if term[0].islower() else f"What {'are' if plural else 'is'} {term}?",
                         body_ext, a, ext_b, si, 0.75)
                continue

            # ---- plain definitions
            m = re.match(r"^•?\s*(?:(An?|The)\s+)?([A-Za-z][\w\-’' ]{1,45}?)\s+(is defined as|is defined to be|refers to|is called|is known as|is said to be)\s+(.{12,})", ps)
            if m and _ok_term(m.group(2)):
                self.add("definition", f"What is {('the ' if m.group(1) and m.group(1).lower() == 'the' else '')}{m.group(2).strip()}?", body_ext, a, ext_b, si, 0.6)
                continue
            m = re.match(r"^•?\s*([A-Z][\w\-’' ()/]{1,40}?)\s*[:–—-]\s+(?:(?:an?|the)\s+)?([a-z].{18,})", ps)
            if m and _ok_term(m.group(1)) and not re.search(r"\d", m.group(1)):
                self.add("definition", f"What is meant by {m.group(1).strip()}?", body_ext, a, ext_b, si, 0.5)
                continue
            m = re.match(r"^•?\s*(An?|The)\s+([a-z][\w\-’' ]{2,40}?)\s+(is an?|is the|are)\s+(.{20,})", ps)
            if m and _ok_term(m.group(2)) and nwords <= 45:
                art = m.group(1).lower()
                self.add("definition", f"What {'are' if m.group(3) == 'are' else 'is'} {art if art == 'the' else ''} {m.group(2)}?".replace("  ", " "),
                         body_ext, a, ext_b, si, 0.42)
                continue

            # ---- formulas written inline
            m = re.match(r"^•?\s*(?:The|An?)?\s*([A-Za-z][\w\-’' ]{2,50}?)\s+(?:is given by|is defined by|is|are|equals|reads|satisfies)\s*:?\s*(\$[^$]*(?:=|\\approx|\\propto|\\equiv)[^$]*\$)", sent)
            if m and _ok_term(m.group(1)):
                self.add("formula", f"What is the formula for {plain(m.group(1))}?", m.group(2), a, b, si, 0.62)
                continue

            # ---- comparisons
            low = ps.lower()
            m = re.search(r"difference between ([^—–,;]{3,60}?) and ([^—–,;]{3,60}?)(?: is | are | lies |:|,|\.|\s[—–-]\s)", ps, re.I)
            if m:
                self.add("comparison", f"What is the difference between {m.group(1).strip()} and {m.group(2).strip()}?", body_ext, a, ext_b, si, 0.72)
                continue
            m = re.match(r"^•?\s*(?:Unlike|In contrast to|Compared (?:to|with)|As opposed to)\s+(.{3,70}?),\s*(.+)$", ps, re.I)
            if m:
                np_ = _np(m.group(2))
                if np_ and np_.lower() not in PRONOUNS and len(np_) > 2:
                    self.add("comparison", f"How does {np_} differ from {m.group(1).strip()}?", body_ext, a, ext_b, si, 0.6)
                    continue
            m = re.match(r"^•?\s*(.{3,70}?)\s+differs? from\s+(.{3,70}?)\s+(?:in that|because|since|by)\s+", ps, re.I)
            if m and _ok_term(m.group(1)):
                self.add("comparison", f"How does {m.group(1).strip()} differ from {m.group(2).strip()}?", body_ext, a, ext_b, si, 0.68)
                continue
            m = re.match(r"^•?\s*(.{12,}?),?\s+(?:whereas|while)\s+(.{12,})$", ps)
            if m and "whereas" in low or (m and re.search(r"\b(more|less|faster|slower|larger|smaller)\b", low)):
                x, y = _np(m.group(1)), _np(m.group(2))
                if x and y and x.lower() != y.lower() and x.split()[0].lower() not in PRONOUNS and y.split()[0].lower() not in PRONOUNS:
                    self.add("comparison", f"Compare {x} and {y}: how do they differ?", body_ext, a, ext_b, si, 0.55)
                    continue

            # ---- explanations
            m = re.match(r"^•?\s*(.{15,180}?),?\s+because\s+(.{10,})$", ps)
            if m:
                q = _why(m.group(1))
                if q:
                    self.add("explanation", q, body_ext, a, ext_b, si, 0.58)
                    continue
            m = re.match(r"^•?\s*The reason (?:that |why )?(.{10,140}?) is (?:that |because )(.{10,})$", ps, re.I)
            if m:
                self.add("explanation", f"Why {m.group(1).strip()}?", body_ext, a, ext_b, si, 0.62)
                continue
            if re.match(r"^(This|That) is (because|why|due to)\b", ps) and k > 0:
                pa, pb = spans[k - 1]
                q = _why(clean(self.text[pa:pb]))
                if q:
                    self.add("explanation", q, self.text[pa:b], pa, b, si, 0.55)
                    continue
            m = re.match(r"^•?\s*(?:The|An?)?\s*(.{8,100}?)\s+(?:is|are|was|were) (?:due to|caused by|a result of)\s+(.{8,})$", ps)
            if m and _ok_term(m.group(1)):
                self.add("explanation", f"What causes {plain(m.group(1))}?", body_ext, a, ext_b, si, 0.52)
                continue

    def display_formulas(self, si: int, s: dict) -> None:
        for m in re.finditer(r"\$\$(.+?)\$\$", self.text[s["start"]:s["end"]], re.S):
            tex = m.group(1).strip()
            fa, fb = s["start"] + m.start(), s["start"] + m.end()
            if not (5 <= len(tex) <= 280) or not re.search(r"=|\\(approx|propto|equiv|le|ge|sim)\b", tex):
                continue
            if self._overlaps(fa, fb):
                continue
            before = self.text[max(s["start"], fa - 450):fa]
            sents = [x for x in re.split(r"(?<=[.!?])\s+", before.strip()) if x.strip()]
            if not sents:
                continue
            ctx = clean(sents[-1])
            pctx = plain(ctx)
            if len(pctx) < 15 or "$$" in ctx:
                continue
            cs = fa - len(before) + before.rfind(sents[-1])
            mm = re.search(r"(?:the|an?|our)\s+([\w\-’' ]{3,60}?)\s+(?:is|are|can be written as|is given by|is defined as|reads|becomes|satisfies|obeys|takes the form)\s*(?:given by|defined (?:as|by)|written as)?\s*[:,]?\s*$", pctx, re.I)
            if mm and _ok_term(mm.group(1)):
                q = f"Write down the expression for the {mm.group(1).strip()}."
                conf = 0.68
            else:
                lead = pctx if len(pctx) <= 170 else "…" + pctx[-170:]
                q = f"Which equation completes this statement? “{lead.rstrip(':,')} …”"
                conf = 0.45
            self.add("formula", q, f"$${tex}$$", max(cs, s["start"]), fb, si, conf)

    def section_concepts(self, si: int, s: dict) -> None:
        title = s.get("title", "")
        t = re.sub(r"^Page \d+ · ", "", title).strip()
        if title.startswith("Page ") and " · " not in title:
            return
        if title.startswith("Page "):
            prev = self.sections[si - 1]["title"] if si > 0 else ""
            if prev.endswith(t):
                return
        if not t or t.lower() in GENERIC_TITLES or len(t) < 4 or len(t) > 80 or re.fullmatch(r"[\d/.\-\s]+", t):
            return
        spans = sentence_spans(self.text, s["start"], s["end"])
        good = [(a, b) for a, b in spans if len(plain(self.text[a:b]).split()) >= 8 and "$$" not in self.text[a:b]]
        if len(good) < 2:
            return
        a, b = good[0][0], good[1][1] if len(good) > 1 else good[0][1]
        if b - a > 650:
            b = good[0][1]
        vs = re.match(r"^(.{3,40}?)\s+(?:vs\.?|versus|and)\s+(.{3,40})$", t, re.I)
        if vs and re.search(r"\bvs\.?|versus\b", t, re.I):
            self.add("comparison", f"Compare {vs.group(1)} and {vs.group(2)}.", self.text[a:b], a, b, si, 0.55)
        else:
            self.add("concept", f"Explain the key idea of “{plain(t)}”.", self.text[a:b], a, b, si, 0.42)

    # ---------------------------------------------------------------- driver
    def run(self) -> list[Card]:
        for si, s in enumerate(self.sections):
            self.theorem_blocks(si, s)
        for si, s in enumerate(self.sections):
            self.sentence_rules(si, s)
            self.display_formulas(si, s)
        for si, s in enumerate(self.sections):
            self.section_concepts(si, s)

        # dedupe and balance types
        seen, uniq = set(), []
        for c in sorted(self.cards, key=lambda c: -c.confidence):
            if c.key() in seen:
                continue
            seen.add(c.key())
            uniq.append(c)
        by_type: dict[str, list[Card]] = {}
        for c in uniq:
            by_type.setdefault(c.card_type, []).append(c)
        chosen: list[Card] = []
        while len(chosen) < self.max_cards and any(by_type.values()):
            for tlist in by_type.values():
                if tlist and len(chosen) < self.max_cards:
                    chosen.append(tlist.pop(0))
        chosen.sort(key=lambda c: c.start)
        return chosen


def generate_cards(text: str, sections: list[dict], max_cards: int = 40) -> list[Card]:
    return Generator(text, sections, max_cards).run()
