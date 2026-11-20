from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..models import Document, DocumentTopic, Flashcard, Topic
from ..processing.topics import shared_headings
from ..serializers import card_out, doc_brief, topic_out

router = APIRouter(prefix="/api/topics", tags=["topics"])
VISIBLE = (Document.status == "collected", Document.review_status != "rejected")


@router.get("")
def list_topics(subject: str | None = None, db: Session = Depends(get_db)):
    stmt = select(Topic)
    if subject:
        stmt = stmt.where(Topic.subject == subject)
    topics = db.scalars(stmt.order_by(Topic.subject, Topic.name)).all()
    doc_rows = db.execute(select(DocumentTopic.topic_id, Document.category, func.count(), func.count(func.distinct(Document.source_id)))
                          .join(Document).where(*VISIBLE).group_by(DocumentTopic.topic_id, Document.category)).all()
    card_rows = db.execute(select(Flashcard.topic_id, Flashcard.category, func.count())
                           .group_by(Flashcard.topic_id, Flashcard.category)).all()
    docs = defaultdict(lambda: {"mit": 0, "student": 0, "sources": 0})
    for tid, cat, n, ns in doc_rows:
        docs[tid][cat] = n
        docs[tid]["sources"] += ns
    cards = defaultdict(lambda: {"mit": 0, "student": 0})
    for tid, cat, n in card_rows:
        cards[tid][cat] = n
    out = []
    for t in topics:
        d, c = docs[t.id], cards[t.id]
        out.append(topic_out(t, documents={"mit": d["mit"], "student": d["student"]},
                             document_count=d["mit"] + d["student"], source_count=d["sources"],
                             flashcards=dict(c), flashcard_count=c["mit"] + c["student"],
                             cross_source=d["mit"] > 0 and d["student"] > 0))
    return out


@router.get("/shared-headings")
def shared(subject: str | None = None, db: Session = Depends(get_db)):
    return shared_headings(db, subject)


@router.get("/{slug}")
def topic_detail(slug: str, db: Session = Depends(get_db)):
    t = db.scalar(select(Topic).where(Topic.slug == slug))
    if not t:
        raise HTTPException(404, "Topic not found")
    links = db.scalars(select(DocumentTopic).join(Document).where(DocumentTopic.topic_id == t.id, *VISIBLE)
                       .options(selectinload(DocumentTopic.document).selectinload(Document.source),
                                selectinload(DocumentTopic.document).selectinload(Document.course),
                                selectinload(DocumentTopic.document).selectinload(Document.topics).selectinload(DocumentTopic.topic))
                       .order_by(DocumentTopic.score.desc())).all()
    documents = []
    for dt in links:
        d = dt.document
        secs = [{"index": i, "title": d.sections[i]["title"], "page": d.sections[i].get("page")}
                for i in (dt.sections or []) if i < len(d.sections or [])]
        documents.append({**doc_brief(d), "score": dt.score, "hits": dt.hits, "matched_sections": secs[:6]})

    # related topics via shared documents (Jaccard)
    my_docs = {dt.document_id for dt in links}
    related = []
    if my_docs:
        rows = db.execute(select(DocumentTopic.topic_id, DocumentTopic.document_id)
                          .where(DocumentTopic.document_id.in_(my_docs), DocumentTopic.topic_id != t.id)).all()
        overlap = defaultdict(set)
        for tid, did in rows:
            overlap[tid].add(did)
        sizes = dict(db.execute(select(DocumentTopic.topic_id, func.count()).where(DocumentTopic.topic_id.in_(list(overlap)))
                                .group_by(DocumentTopic.topic_id)).all()) if overlap else {}
        for tid, ds in overlap.items():
            jac = len(ds) / (len(my_docs) + sizes.get(tid, 0) - len(ds))
            related.append((tid, round(jac, 3), len(ds)))
        related.sort(key=lambda x: -x[1])
        rel_topics = {x.id: x for x in db.scalars(select(Topic).where(Topic.id.in_([r[0] for r in related[:8]]))).all()}
        related = [topic_out(rel_topics[tid], similarity=j, shared_documents=n) for tid, j, n in related[:8]]

    cards = {}
    for cat in ("mit", "student"):
        cs = db.scalars(select(Flashcard).where(Flashcard.topic_id == t.id, Flashcard.category == cat)
                        .order_by(Flashcard.confidence.desc()).limit(6)).all()
        cards[cat] = [card_out(c) for c in cs]
    counts = dict(db.execute(select(Flashcard.category, func.count()).where(Flashcard.topic_id == t.id)
                             .group_by(Flashcard.category)).all())
    return {**topic_out(t), "documents": documents, "related": related, "flashcards": cards,
            "flashcard_counts": {"mit": counts.get("mit", 0), "student": counts.get("student", 0)},
            "coverage": {"mit": sum(1 for d in documents if d["category"] == "mit"),
                         "student": sum(1 for d in documents if d["category"] == "student"),
                         "sources": len({d["source"]["id"] for d in documents if d["source"]})}}
