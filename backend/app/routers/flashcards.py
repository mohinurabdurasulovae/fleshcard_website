import csv
import io
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..criteria import CRITERIA
from ..db import get_db
from ..models import Course, Document, Evaluation, Flashcard, Source, Topic
from ..serializers import card_out, eval_out

router = APIRouter(prefix="/api", tags=["flashcards"])
CRITERIA_KEYS = {c["key"] for c in CRITERIA}


def _card_query(category=None, subject=None, document_id=None, card_type=None, topic=None, course_id=None,
                source=None, q=None):
    stmt = select(Flashcard).join(Flashcard.document).where(Document.status == "collected",
                                                            Document.review_status != "rejected")
    if category:
        stmt = stmt.where(Flashcard.category == category)
    if subject:
        stmt = stmt.where(Flashcard.subject == subject)
    if document_id:
        stmt = stmt.where(Flashcard.document_id == document_id)
    if card_type:
        stmt = stmt.where(Flashcard.card_type == card_type)
    if topic:
        stmt = stmt.join(Topic, Topic.id == Flashcard.topic_id).where(Topic.slug == topic)
    if course_id:
        stmt = stmt.where(Document.course_id == course_id)
    if source:
        stmt = stmt.join(Source, Source.id == Document.source_id).where(Source.key == source)
    if q:
        stmt = stmt.where(Flashcard.question.ilike(f"%{q}%") | Flashcard.answer.ilike(f"%{q}%"))
    return stmt


LOAD = (selectinload(Flashcard.document).selectinload(Document.source),
        selectinload(Flashcard.document).selectinload(Document.course),
        selectinload(Flashcard.topic), selectinload(Flashcard.evaluations))


@router.get("/flashcards")
def list_cards(category: str | None = None, subject: str | None = None, document_id: int | None = None,
               card_type: str | None = None, topic: str | None = None, course_id: int | None = None,
               source: str | None = None, q: str | None = None, unrated_by: str | None = None,
               order: str = "document", limit: int = 30, offset: int = 0, db: Session = Depends(get_db)):
    stmt = _card_query(category, subject, document_id, card_type, topic, course_id, source, q)
    if unrated_by:
        rated = select(Evaluation.flashcard_id).where(Evaluation.evaluator == unrated_by)
        stmt = stmt.where(Flashcard.id.not_in(rated))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    ordering = {"random": func.random(), "confidence": Flashcard.confidence.desc(),
                "document": (Flashcard.document_id, Flashcard.char_start)}.get(order, (Flashcard.document_id, Flashcard.char_start))
    ordering = ordering if isinstance(ordering, tuple) else (ordering,)
    cards = db.scalars(stmt.options(*LOAD).order_by(*ordering).offset(offset).limit(min(limit, 200))).all()
    return {"total": total, "items": [card_out(c) for c in cards]}


@router.get("/flashcards/decks")
def decks(category: str | None = None, subject: str | None = None, db: Session = Depends(get_db)):
    """Documents that have flashcards, grouped as study decks."""
    stmt = (select(Document, func.count(Flashcard.id)).join(Flashcard).where(Document.status == "collected",
                                                                             Document.review_status != "rejected")
            .options(selectinload(Document.course), selectinload(Document.source)).group_by(Document.id))
    if category:
        stmt = stmt.where(Document.category == category)
    if subject:
        stmt = stmt.where(Document.subject == subject)
    rows = db.execute(stmt.order_by(Document.subject, Document.title)).all()
    return [{"document_id": d.id, "title": d.title, "category": d.category, "subject": d.subject,
             "course": f"{d.course.code} · {d.course.title}" if d.course else "", "source": d.source.name,
             "count": n} for d, n in rows]


@router.get("/flashcards/export")
def export_cards(format: str = "csv", category: str | None = None, subject: str | None = None,
                 db: Session = Depends(get_db)):
    cards = db.scalars(_card_query(category, subject).options(*LOAD).order_by(Flashcard.id)).all()
    rows = [{"id": c.id, "category": c.category, "subject": c.subject, "type": c.card_type, "question": c.question,
             "answer": c.answer, "source": c.document.source.name, "document": c.document.title,
             "document_url": c.document.url, "section": c.section_title, "page": c.page,
             "topic": c.topic.name if c.topic else "", "generator": c.generator} for c in cards]
    return _export(rows, format, "flashcards")


def _export(rows: list[dict], fmt: str, name: str, extra: dict | None = None) -> Response:
    if fmt == "json":
        body = json.dumps({**(extra or {}), name: rows}, indent=2, ensure_ascii=False, default=str)
        return Response(body, media_type="application/json",
                        headers={"Content-Disposition": f'attachment; filename="{name}.json"'})
    buf = io.StringIO()
    if rows:
        w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return Response("﻿" + buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{name}.csv"'})


@router.get("/flashcards/{card_id}")
def get_card(card_id: int, db: Session = Depends(get_db)):
    c = db.get(Flashcard, card_id)
    if not c:
        raise HTTPException(404)
    out = card_out(c)
    out["evaluation_list"] = [eval_out(e) for e in sorted(c.evaluations, key=lambda e: e.created_at, reverse=True)]
    return out


class CardPatch(BaseModel):
    question: str | None = None
    answer: str | None = None
    card_type: str | None = None


@router.patch("/flashcards/{card_id}")
def edit_card(card_id: int, body: CardPatch, db: Session = Depends(get_db)):
    c = db.get(Flashcard, card_id)
    if not c:
        raise HTTPException(404)
    for k, v in body.model_dump(exclude_unset=True).items():
        if v:
            setattr(c, k, v)
    c.generator = c.generator if c.generator.endswith("+edited") else c.generator + "+edited"
    db.commit()
    return card_out(c)


@router.delete("/flashcards/{card_id}")
def delete_card(card_id: int, db: Session = Depends(get_db)):
    c = db.get(Flashcard, card_id)
    if not c:
        raise HTTPException(404)
    db.delete(c)
    db.commit()
    return {"ok": True}


# ------------------------------------------------------------------ evaluations
class EvaluationIn(BaseModel):
    flashcard_id: int
    overall: int = Field(ge=1, le=5)
    criteria: dict[str, int] = {}
    comment: str = ""
    evaluator: str = "anonymous"


@router.post("/evaluations")
def create_evaluation(body: EvaluationIn, db: Session = Depends(get_db)):
    if not db.get(Flashcard, body.flashcard_id):
        raise HTTPException(404, "Flashcard not found")
    crit = {k: int(v) for k, v in body.criteria.items() if k in CRITERIA_KEYS and 1 <= int(v) <= 5}
    evaluator = (body.evaluator or "anonymous").strip()[:120] or "anonymous"
    existing = db.scalar(select(Evaluation).where(Evaluation.flashcard_id == body.flashcard_id,
                                                  Evaluation.evaluator == evaluator)) if evaluator != "anonymous" else None
    e = existing or Evaluation(flashcard_id=body.flashcard_id, evaluator=evaluator)
    e.overall, e.criteria, e.comment = body.overall, crit, body.comment.strip()[:5000]
    if not existing:
        db.add(e)
    db.commit()
    return {**eval_out(e), "updated": bool(existing)}


@router.get("/evaluations")
def list_evaluations(flashcard_id: int | None = None, evaluator: str | None = None, category: str | None = None,
                     limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    stmt = select(Evaluation).join(Evaluation.flashcard)
    if flashcard_id:
        stmt = stmt.where(Evaluation.flashcard_id == flashcard_id)
    if evaluator:
        stmt = stmt.where(Evaluation.evaluator == evaluator)
    if category:
        stmt = stmt.where(Flashcard.category == category)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.options(selectinload(Evaluation.flashcard).selectinload(Flashcard.document))
                      .order_by(Evaluation.created_at.desc()).offset(offset).limit(limit)).all()
    return {"total": total, "items": [{**eval_out(e), "question": e.flashcard.question, "category": e.flashcard.category,
                                       "card_type": e.flashcard.card_type, "document": e.flashcard.document.title}
                                      for e in rows]}


@router.delete("/evaluations/{eval_id}")
def delete_evaluation(eval_id: int, db: Session = Depends(get_db)):
    e = db.get(Evaluation, eval_id)
    if not e:
        raise HTTPException(404)
    db.delete(e)
    db.commit()
    return {"ok": True}


@router.get("/evaluations/next")
def next_card(evaluator: str = "anonymous", category: str | None = None, subject: str | None = None,
              card_type: str | None = None, document_id: int | None = None, exclude: str = "",
              db: Session = Depends(get_db)):
    """Next flashcard this evaluator has not rated yet (least-evaluated first, then random)."""
    stmt = _card_query(category, subject, document_id, card_type)
    rated = select(Evaluation.flashcard_id).where(Evaluation.evaluator == evaluator)
    stmt = stmt.where(Flashcard.id.not_in(rated))
    skip = [int(x) for x in exclude.split(",") if x.strip().isdigit()]
    if skip:
        stmt = stmt.where(Flashcard.id.not_in(skip))
    remaining = db.scalar(select(func.count()).select_from(stmt.subquery()))
    n_evals = select(func.count(Evaluation.id)).where(Evaluation.flashcard_id == Flashcard.id).scalar_subquery()
    c = db.scalar(stmt.options(*LOAD).order_by(n_evals, func.random()).limit(1))
    done = db.scalar(select(func.count()).select_from(Evaluation).where(Evaluation.evaluator == evaluator))
    return {"card": card_out(c) if c else None, "remaining": remaining, "rated_by_you": done}
