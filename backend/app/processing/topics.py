"""Keyword-based topic assignment, document similarity and cross-source heading matching."""

from __future__ import annotations

import math
import re
from bisect import bisect_right
from collections import Counter, defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Document, DocumentTopic, Topic

STOPWORDS = set("""
a about above after again against all also am an and any are as at be because been before being below between both but
by can cannot could did do does doing down during each few for from further had has have having he her here hers him his
how i if in into is it its itself just let me more most my no nor not now of off on once only or other our ours out over
own same she should so some such than that the their them then there these they this those through to too under until up
very was we were what when where which while who whom why will with would you your yours one two may might must shall
thus hence therefore however since get got given gives use used using like well first second also see note example
let us we'll i.e e.g etc page lecture chapter section figure eq equation thing things way ways make makes made want need
case cases new time number value values set sets called define defined definition theorem lemma proof proposition
""".split())


def _topic_regex(keywords: list[str]) -> re.Pattern:
    alts = sorted({re.escape(k.lower()) for k in keywords}, key=len, reverse=True)
    return re.compile(r"(?<![a-z])(?:" + "|".join(alts) + r")(?:s|es)?(?![a-z])")


_cache: dict[int, re.Pattern] = {}


def topic_pattern(t: Topic) -> re.Pattern:
    key = hash((t.id, tuple(t.keywords or [])))
    if key not in _cache:
        _cache[key] = _topic_regex(t.keywords or [t.name])
    return _cache[key]


def assign_topics(db: Session, doc: Document, max_topics: int = 6) -> list[DocumentTopic]:
    for dt in list(doc.topics):
        db.delete(dt)
    db.flush()
    topics = db.scalars(select(Topic).where(Topic.subject == doc.subject)).all()
    text = (doc.text or "").lower()
    title = (doc.title or "").lower()
    if not text or not topics:
        return []
    starts = [s["start"] for s in (doc.sections or [])]
    words = max(len(text.split()), 1)
    scored = []
    for t in topics:
        pat = topic_pattern(t)
        sec_hits: Counter = Counter()
        hits = 0
        for m in pat.finditer(text):
            hits += 1
            if starts:
                sec_hits[max(bisect_right(starts, m.start()) - 1, 0)] += 1
        title_bonus = 3 if pat.search(title) else 0
        density = hits / (words / 1000)
        score = density + title_bonus * 2
        if hits >= 4 and (density >= 0.4 or title_bonus):
            scored.append((score, hits, t, [i for i, _ in sec_hits.most_common(8)]))
    scored.sort(key=lambda x: -x[0])
    out = []
    for score, hits, t, secs in scored[:max_topics]:
        dt = DocumentTopic(document_id=doc.id, topic_id=t.id, score=round(score, 3), hits=hits, sections=secs)
        db.add(dt)
        out.append(dt)
    db.flush()
    return out


def best_topic_for_text(text: str, candidates: list[Topic]) -> Topic | None:
    best, best_hits = None, 0
    low = text.lower()
    for t in candidates:
        n = len(topic_pattern(t).findall(low))
        if n > best_hits:
            best, best_hits = t, n
    return best


# --------------------------------------------------------------------------- similarity
_WORD = re.compile(r"[a-zA-Z][a-zA-Z\-]{2,}")


def top_terms(text: str, n: int = 80) -> dict[str, float]:
    text = re.sub(r"\$\$.+?\$\$|\$[^$\n]+?\$", " ", text, flags=re.S)
    counts = Counter(w.lower().strip("-") for w in _WORD.findall(text))
    for s in list(counts):
        if s in STOPWORDS or len(s) < 3:
            del counts[s]
    total = sum(counts.values()) or 1
    return {w: round(c / total, 6) for w, c in counts.most_common(n)}


def similar_documents(db: Session, doc: Document, limit: int = 6) -> list[tuple[Document, float]]:
    docs = db.scalars(select(Document).where(Document.status == "collected", Document.review_status != "rejected")).all()
    vecs = {d.id: (d.meta or {}).get("terms") or {} for d in docs}
    n = len(docs) or 1
    df: Counter = Counter()
    for v in vecs.values():
        df.update(v.keys())

    def tfidf(v: dict) -> dict:
        return {w: tf * math.log((n + 1) / (df[w] + 1)) for w, tf in v.items()}

    base = tfidf(vecs.get(doc.id) or top_terms(doc.text or ""))
    bn = math.sqrt(sum(x * x for x in base.values())) or 1
    out = []
    for d in docs:
        if d.id == doc.id:
            continue
        v = tfidf(vecs[d.id])
        dot = sum(base.get(w, 0) * x for w, x in v.items())
        vn = math.sqrt(sum(x * x for x in v.values())) or 1
        sim = dot / (bn * vn)
        if sim > 0.05:
            out.append((d, round(sim, 3)))
    out.sort(key=lambda x: -x[1])
    return out[:limit]


# --------------------------------------------------------------------------- shared headings
GENERIC = {"introduction", "summary", "overview", "conclusion", "untitled section", "notation", "preliminaries",
           "examples", "example", "exercises", "problems", "appendix", "references", "contents", "recap", "review",
           "motivation", "background", "notes", "lecture", "outline", "admin", "logistics", "definitions"}


def normalize_heading(h: str) -> str:
    h = h.lower()
    h = re.sub(r"^page \d+( · )?", "", h)
    h = re.sub(r"\$[^$]*\$", "", h)
    h = re.sub(r"^(lecture|chapter|section|part|week)\s*\d+[:.\-–]?\s*", "", h)
    h = re.sub(r"^[\divxlc]+(\.\d+)*[.):]?\s+", "", h)
    h = re.sub(r"[^a-z0-9' ]+", " ", h)
    words = [w for w in h.split() if w not in {"the", "a", "an", "of", "and", "to", "in", "on", "for"}]
    words = [w[:-1] if w.endswith("s") and len(w) > 4 else w for w in words]
    return " ".join(words)


def shared_headings(db: Session, subject: str | None = None, min_sources: int = 2, limit: int = 60) -> list[dict]:
    q = select(Document).where(Document.status == "collected", Document.review_status != "rejected")
    if subject:
        q = q.where(Document.subject == subject)
    groups: dict[str, dict] = defaultdict(lambda: {"titles": Counter(), "docs": {}, "sources": set(), "categories": set()})
    for d in db.scalars(q).all():
        seen = set()
        for i, s in enumerate(d.sections or []):
            norm = normalize_heading(s.get("title", ""))
            if not norm or norm in GENERIC or len(norm) < 4 or norm in seen or re.fullmatch(r"[\d ]+", norm):
                continue
            seen.add(norm)
            g = groups[norm]
            g["titles"][s["title"]] += 1
            g["docs"].setdefault(d.id, {"id": d.id, "title": d.title, "category": d.category, "section_index": i,
                                        "source_id": d.source_id, "subject": d.subject})
            g["sources"].add(d.source_id)
            g["categories"].add(d.category)
    out = []
    for norm, g in groups.items():
        if len(g["sources"]) >= min_sources:
            out.append({
                "key": norm,
                "label": g["titles"].most_common(1)[0][0].split(" · ")[-1],
                "source_count": len(g["sources"]),
                "categories": sorted(g["categories"]),
                "documents": list(g["docs"].values())[:12],
                "document_count": len(g["docs"]),
            })
    out.sort(key=lambda x: (-x["source_count"], -len(x["categories"]), -x["document_count"]))
    return out[:limit]
