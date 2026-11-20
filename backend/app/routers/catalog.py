import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from ..config import get_settings
from ..criteria import CARD_TYPES, CRITERIA, RATING_SCALE
from ..db import get_db
from ..models import Course, Document, DocumentTopic, Evaluation, Flashcard, Source, Topic
from ..seed import SUBJECTS
from ..serializers import course_out, doc_brief, source_out, topic_out

router = APIRouter(prefix="/api", tags=["catalog"])

VISIBLE = (Document.status == "collected", Document.review_status != "rejected")


@router.get("/meta")
def meta():
    s = get_settings()
    return {"subjects": SUBJECTS, "criteria": CRITERIA, "rating_scale": RATING_SCALE, "card_types": CARD_TYPES,
            "ai": {"enabled": s.ai_enabled, "provider": s.ai_provider,
                   "model": s.anthropic_model if s.ai_provider == "anthropic" else s.openai_model}}


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    def count(model, *where):
        return db.scalar(select(func.count()).select_from(model).where(*where)) or 0

    cat_docs = dict(db.execute(select(Document.category, func.count()).where(*VISIBLE).group_by(Document.category)).all())
    cat_cards = dict(db.execute(select(Flashcard.category, func.count()).group_by(Flashcard.category)).all())
    cat_courses = dict(db.execute(select(Source.category, func.count(Course.id)).join(Course.source).group_by(Source.category)).all())
    cat_words = dict(db.execute(select(Document.category, func.sum(Document.word_count)).where(*VISIBLE).group_by(Document.category)).all())

    by_subject = []
    for subj in SUBJECTS:
        row = {"subject": subj}
        for cat in ("mit", "student"):
            row[f"{cat}_documents"] = count(Document, *VISIBLE, Document.subject == subj, Document.category == cat)
            row[f"{cat}_flashcards"] = count(Flashcard, Flashcard.subject == subj, Flashcard.category == cat)
            row[f"{cat}_courses"] = db.scalar(select(func.count(Course.id)).join(Course.source).where(
                Course.subject == subj, Source.category == cat)) or 0
        by_subject.append(row)

    by_type = [{"type": t, "mit": 0, "student": 0} for t in [c["key"] for c in CARD_TYPES]]
    for t, cat, n in db.execute(select(Flashcard.card_type, Flashcard.category, func.count()).group_by(Flashcard.card_type, Flashcard.category)):
        for row in by_type:
            if row["type"] == t:
                row[cat] = n

    recent = db.scalars(select(Document).where(*VISIBLE).options(selectinload(Document.topics).selectinload(DocumentTopic.topic),
                                                                 selectinload(Document.source), selectinload(Document.course))
                        .order_by(Document.created_at.desc()).limit(8)).all()

    top_topics = db.execute(select(Topic, func.count(DocumentTopic.document_id).label("n")).join(DocumentTopic)
                            .group_by(Topic.id).order_by(func.count(DocumentTopic.document_id).desc()).limit(8)).all()
    sources = db.execute(select(Source, func.count(Document.id)).outerjoin(Document, (Document.source_id == Source.id) & (Document.status == "collected"))
                         .group_by(Source.id).order_by(func.count(Document.id).desc())).all()
    return {
        "totals": {
            "courses": count(Course), "documents": sum(cat_docs.values()), "flashcards": sum(cat_cards.values()),
            "evaluations": count(Evaluation), "topics": db.scalar(select(func.count(func.distinct(DocumentTopic.topic_id)))) or 0,
            "sources": count(Source), "failed": count(Document, Document.status == "failed"),
            "words": int(sum(v or 0 for v in cat_words.values())),
        },
        "by_category": {cat: {"documents": cat_docs.get(cat, 0), "flashcards": cat_cards.get(cat, 0),
                              "courses": cat_courses.get(cat, 0), "words": int(cat_words.get(cat) or 0)}
                        for cat in ("mit", "student")},
        "by_subject": by_subject,
        "by_card_type": by_type,
        "recent_documents": [doc_brief(d) for d in recent],
        "top_topics": [topic_out(t, document_count=n) for t, n in top_topics],
        "sources": [{**source_out(s), "document_count": n} for s, n in sources],
    }


@router.get("/sources")
def sources(db: Session = Depends(get_db)):
    rows = db.execute(select(Source, func.count(Document.id)).outerjoin(Document, (Document.source_id == Source.id) & (Document.status == "collected"))
                      .group_by(Source.id).order_by(Source.category, Source.name)).all()
    return [{**source_out(s), "document_count": n} for s, n in rows]


@router.get("/universities")
def universities(db: Session = Depends(get_db)):
    return sorted({u for (u,) in db.execute(select(Course.university).distinct()) if u})


@router.get("/courses")
def courses(subject: str | None = None, category: str | None = None, university: str | None = None,
            source: str | None = None, q: str | None = None, has_documents: bool = False,
            page: int = 1, page_size: int = 24, db: Session = Depends(get_db)):
    doc_counts = (select(Document.course_id, func.count(Document.id).label("n")).where(*VISIBLE)
                  .group_by(Document.course_id).subquery())
    card_counts = (select(Document.course_id, func.count(Flashcard.id).label("c")).join(Flashcard)
                   .where(*VISIBLE).group_by(Document.course_id).subquery())
    stmt = (select(Course, func.coalesce(doc_counts.c.n, 0), func.coalesce(card_counts.c.c, 0)).join(Course.source)
            .outerjoin(doc_counts, doc_counts.c.course_id == Course.id)
            .outerjoin(card_counts, card_counts.c.course_id == Course.id))
    if subject:
        stmt = stmt.where(Course.subject == subject)
    if category:
        stmt = stmt.where(Source.category == category)
    if university:
        stmt = stmt.where(Course.university == university)
    if source:
        stmt = stmt.where(Source.key == source)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Course.title.ilike(like), Course.code.ilike(like), Course.description.ilike(like),
                              Course.instructors.ilike(like)))
    if has_documents:
        stmt = stmt.where(doc_counts.c.n > 0)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.execute(stmt.order_by(func.coalesce(doc_counts.c.n, 0).desc(), Course.subject, Course.code)
                      .offset((page - 1) * page_size).limit(page_size)).all()
    return {"total": total, "page": page, "page_size": page_size,
            "items": [course_out(c, n, cc) for c, n, cc in rows]}


@router.get("/courses/{course_id}")
def course_detail(course_id: int, db: Session = Depends(get_db)):
    c = db.get(Course, course_id)
    if not c:
        raise HTTPException(404, "Course not found")
    docs = db.scalars(select(Document).where(Document.course_id == c.id).options(
        selectinload(Document.topics).selectinload(DocumentTopic.topic)).order_by(Document.title)).all()
    counts = dict(db.execute(select(Flashcard.document_id, func.count()).where(Flashcard.document_id.in_([d.id for d in docs]))
                             .group_by(Flashcard.document_id)).all()) if docs else {}
    return {**course_out(c, len(docs), sum(counts.values())), "documents": [doc_brief(d, counts.get(d.id, 0)) for d in docs]}


class CourseIn(BaseModel):
    source_key: str | None = None
    code: str | None = None
    title: str | None = None
    subject: str | None = None
    university: str | None = None
    url: str | None = None
    description: str | None = None
    instructors: str | None = None
    term: str | None = None
    license: str | None = None


@router.post("/courses")
def create_course(body: CourseIn, db: Session = Depends(get_db)):
    src = db.scalar(select(Source).where(Source.key == (body.source_key or "mit-ocw")))
    if not src or not body.code or not body.title or body.subject not in SUBJECTS:
        raise HTTPException(400, "source_key, code, title and a valid subject are required")
    c = Course(source_id=src.id, **{k: v for k, v in body.model_dump().items() if k != "source_key" and v is not None})
    db.add(c)
    db.commit()
    return course_out(c)


@router.patch("/courses/{course_id}")
def update_course(course_id: int, body: CourseIn, db: Session = Depends(get_db)):
    c = db.get(Course, course_id)
    if not c:
        raise HTTPException(404)
    for k, v in body.model_dump(exclude_unset=True).items():
        if k != "source_key" and v is not None:
            setattr(c, k, v)
    db.commit()
    return course_out(c)


@router.delete("/courses/{course_id}")
def delete_course(course_id: int, db: Session = Depends(get_db)):
    c = db.get(Course, course_id)
    if not c:
        raise HTTPException(404)
    db.delete(c)
    db.commit()
    return {"ok": True}


def _snippet(text: str, q: str, width: int = 110) -> str:
    m = re.search(re.escape(q), text, re.I)
    if not m:
        return ""
    a, b = max(0, m.start() - width), min(len(text), m.end() + width)
    return ("…" if a else "") + re.sub(r"\s+", " ", text[a:b]) + ("…" if b < len(text) else "")


@router.get("/search")
def search(q: str, limit: int = 12, db: Session = Depends(get_db)):
    if len(q.strip()) < 2:
        return {"documents": [], "courses": [], "topics": [], "flashcards": []}
    like = f"%{q}%"
    docs = db.scalars(select(Document).where(*VISIBLE, or_(Document.title.ilike(like), Document.text.ilike(like)))
                      .options(selectinload(Document.source), selectinload(Document.course),
                               selectinload(Document.topics).selectinload(DocumentTopic.topic))
                      .order_by(Document.title.ilike(like).desc()).limit(limit)).all()
    courses_ = db.scalars(select(Course).where(or_(Course.title.ilike(like), Course.code.ilike(like))).limit(8)).all()
    topics = db.scalars(select(Topic).where(Topic.name.ilike(like)).limit(8)).all()
    cards = db.scalars(select(Flashcard).where(or_(Flashcard.question.ilike(like), Flashcard.answer.ilike(like))).limit(8)).all()
    return {
        "documents": [{**doc_brief(d), "snippet": _snippet(d.text, q)} for d in docs],
        "courses": [course_out(c) for c in courses_],
        "topics": [topic_out(t) for t in topics],
        "flashcards": [{"id": c.id, "question": c.question, "category": c.category, "document_id": c.document_id}
                       for c in cards],
    }
