import hashlib
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from ..collectors.base import Candidate, SkipDocument
from ..config import get_settings
from ..db import get_db
from ..models import Document, DocumentTopic, Flashcard, Source
from ..pipeline import build_flashcards, process_document_content
from ..processing.topics import similar_documents
from ..seed import SUBJECTS
from ..serializers import doc_brief

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("")
def list_documents(subject: str | None = None, category: str | None = None, source: str | None = None,
                   course_id: int | None = None, topic: str | None = None, q: str | None = None,
                   status: str | None = "collected", review: str | None = None, fmt: str | None = None,
                   sort: str = "recent", page: int = 1, page_size: int = 24, db: Session = Depends(get_db)):
    stmt = select(Document).join(Document.source)
    if status and status != "all":
        stmt = stmt.where(Document.status == status)
    if review:
        stmt = stmt.where(Document.review_status == review)
    elif status == "collected":
        stmt = stmt.where(Document.review_status != "rejected")
    if subject:
        stmt = stmt.where(Document.subject == subject)
    if category:
        stmt = stmt.where(Document.category == category)
    if source:
        stmt = stmt.where(Source.key == source)
    if course_id:
        stmt = stmt.where(Document.course_id == course_id)
    if fmt:
        stmt = stmt.where(Document.format == fmt)
    if topic:
        from ..models import Topic
        stmt = stmt.join(DocumentTopic, DocumentTopic.document_id == Document.id).join(Topic).where(Topic.slug == topic)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Document.title.ilike(like), Document.summary.ilike(like), Document.author.ilike(like),
                              Document.text.ilike(like)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    order = {"recent": Document.created_at.desc(), "title": Document.title.asc(),
             "words": Document.word_count.desc()}.get(sort, Document.created_at.desc())
    docs = db.scalars(stmt.options(selectinload(Document.source), selectinload(Document.course),
                                   selectinload(Document.topics).selectinload(DocumentTopic.topic))
                      .order_by(order).offset((page - 1) * page_size).limit(page_size)).all()
    counts = dict(db.execute(select(Flashcard.document_id, func.count()).where(Flashcard.document_id.in_([d.id for d in docs]))
                             .group_by(Flashcard.document_id)).all()) if docs else {}
    return {"total": total, "page": page, "page_size": page_size,
            "items": [doc_brief(d, counts.get(d.id, 0)) for d in docs]}


def _get(db, doc_id) -> Document:
    d = db.get(Document, doc_id)
    if not d:
        raise HTTPException(404, "Document not found")
    return d


@router.get("/{doc_id}")
def document_detail(doc_id: int, db: Session = Depends(get_db)):
    d = _get(db, doc_id)
    n_cards = db.scalar(select(func.count()).where(Flashcard.document_id == d.id))
    by_cat = dict(db.execute(select(Flashcard.card_type, func.count()).where(Flashcard.document_id == d.id)
                             .group_by(Flashcard.card_type)).all())
    topic_sections = [{"topic": {"id": dt.topic.id, "slug": dt.topic.slug, "name": dt.topic.name},
                       "score": dt.score, "hits": dt.hits, "sections": dt.sections}
                      for dt in sorted(d.topics, key=lambda x: -x.score)]
    similar = [{**doc_brief(x), "similarity": s} for x, s in similar_documents(db, d)]
    return {**doc_brief(d, n_cards),
            "sections": [{k: v for k, v in s.items()} for s in d.sections],
            "topic_sections": topic_sections, "card_types": by_cat, "similar": similar,
            "katex_macros": (d.meta or {}).get("katex_macros", {}),
            "repo_path": ((d.meta or {}).get("candidate") or {}).get("meta", {}).get("path")}


@router.get("/{doc_id}/content")
def document_content(doc_id: int, db: Session = Depends(get_db)):
    d = _get(db, doc_id)
    return {"id": d.id, "title": d.title, "length": len(d.text or ""),
            "sections": [{**s, "index": i, "text": d.text[s["start"]:s["end"]]} for i, s in enumerate(d.sections or [])],
            "katex_macros": (d.meta or {}).get("katex_macros", {})}


@router.get("/{doc_id}/file")
def document_file(doc_id: int, db: Session = Depends(get_db)):
    d = _get(db, doc_id)
    if not d.local_path:
        raise HTTPException(404, "No stored file")
    p = get_settings().data_path / d.local_path
    if not p.is_file():
        raise HTTPException(404, "Stored file missing")
    media = {"pdf": "application/pdf", "html": "text/html; charset=utf-8", "md": "text/plain; charset=utf-8",
             "tex": "text/plain; charset=utf-8"}.get(d.format, "application/octet-stream")
    headers = {"Content-Disposition": "inline"}
    if d.format == "html":
        headers["Content-Security-Policy"] = "script-src 'none'"
    return FileResponse(p, media_type=media, headers=headers)


class DocumentPatch(BaseModel):
    title: str | None = None
    subject: str | None = None
    review_status: str | None = None
    author: str | None = None
    license: str | None = None
    course_id: int | None = None


@router.patch("/{doc_id}")
def update_document(doc_id: int, body: DocumentPatch, db: Session = Depends(get_db)):
    d = _get(db, doc_id)
    data = body.model_dump(exclude_unset=True)
    if "review_status" in data and data["review_status"] not in ("pending", "approved", "rejected"):
        raise HTTPException(400, "invalid review_status")
    if "subject" in data and data["subject"] not in SUBJECTS:
        raise HTTPException(400, "invalid subject")
    for k, v in data.items():
        setattr(d, k, v)
    if "subject" in data:
        for c in d.flashcards:
            c.subject = d.subject
    db.commit()
    return doc_brief(d)


@router.delete("/{doc_id}")
def delete_document(doc_id: int, db: Session = Depends(get_db)):
    d = _get(db, doc_id)
    db.delete(d)
    db.commit()
    return {"ok": True}


class GenerateIn(BaseModel):
    use_ai: bool = False
    max_cards: int = 40


@router.post("/{doc_id}/flashcards/generate")
def generate(doc_id: int, body: GenerateIn, db: Session = Depends(get_db)):
    d = _get(db, doc_id)
    if d.status != "collected":
        raise HTTPException(400, "Document has no text yet")
    if body.use_ai and not get_settings().ai_enabled:
        raise HTTPException(400, "AI generation is not configured. Set AI_PROVIDER and an API key in backend/.env")
    try:
        n = build_flashcards(db, d, use_ai=body.use_ai, max_cards=body.max_cards)
    except Exception as e:  # noqa: BLE001
        db.rollback()
        raise HTTPException(502, f"Generation failed: {e}")
    db.commit()
    total = db.scalar(select(func.count()).where(Flashcard.document_id == d.id))
    return {"created": n, "total": total}


@router.post("/upload")
async def upload(file: UploadFile = File(...), subject: str = Form(...), source_key: str = Form("manual-upload"),
                 title: str = Form(""), course_code: str = Form("General"), course_title: str = Form(""),
                 university: str = Form(""), author: str = Form(""), license: str = Form(""), url: str = Form(""),
                 category: str = Form("student"), db: Session = Depends(get_db)):
    if subject not in SUBJECTS:
        raise HTTPException(400, "invalid subject")
    src = db.scalar(select(Source).where(Source.key == source_key))
    if not src:
        src = Source(key=source_key, name="Uploaded MIT OCW notes" if category == "mit" else "Uploaded student notes",
                     category=category if category in ("mit", "student") else "student", kind="upload",
                     url="", subjects=SUBJECTS, description="Documents uploaded through the admin page.")
        db.add(src)
        db.flush()
    data = await file.read()
    name = file.filename or "upload"
    fmt = Path(name).suffix.lower().lstrip(".")
    fmt = {"markdown": "md", "htm": "html"}.get(fmt, fmt)
    if fmt not in ("pdf", "md", "tex", "html"):
        raise HTTPException(400, "Supported formats: PDF, HTML, Markdown, LaTeX")
    doc_url = url or f"upload://{hashlib.sha1(data).hexdigest()[:12]}/{name}"
    cand = Candidate(url=doc_url, title=title or Path(name).stem, subject=subject, fmt=fmt, course_code=course_code,
                     course_title=course_title or course_code, university=university, author=author,
                     license=license or "Provided by uploader")
    doc = Document(source_id=src.id, category=src.category, subject=subject, title=cand.title, url=doc_url,
                   meta={"candidate": cand.to_meta()})
    db.add(doc)
    db.flush()
    try:
        process_document_content(db, doc, data, cand, src, {"generate_flashcards": True})
    except SkipDocument as e:
        db.rollback()
        raise HTTPException(400, str(e))
    except Exception as e:  # noqa: BLE001
        db.rollback()
        raise HTTPException(400, f"Could not process file: {e}")
    db.commit()
    return doc_brief(doc)
