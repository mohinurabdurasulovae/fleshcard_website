"""Turn a collector Candidate into a stored, processed Document (+ topics + flashcards)."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .collectors.base import Candidate, Fetcher, SkipDocument
from .config import get_settings
from .models import Course, Document, Flashcard, Source, Topic
from .processing import ai
from .processing.extract import detect_format, extract
from .processing.flashcards import generate_cards
from .processing.topics import assign_topics, best_topic_for_text, top_terms

MIN_WORDS = 120


def _good_title(t: str) -> bool:
    t = (t or "").strip()
    return 3 <= len(t) <= 200 and len(re.findall(r"[A-Za-z]", t)) >= 4 and "\\" not in t and not re.search(
        r"lectures? by|notes taken|^untitled|microsoft word|^slide \d", t, re.I)


def _good_author(a: str) -> bool:
    a = (a or "").strip()
    return 2 <= len(a) <= 80 and not re.search(r"@|https?:|\\|lectures? by|notes taken|report typos|^unknown$", a, re.I)


def upsert_course(db: Session, source: Source, cand: Candidate, doc_title: str = "") -> Course:
    code = (cand.course_code or "General").strip()[:120]
    title = cand.course_title or code
    if "{doc_title}" in title:
        title = doc_title or code
    course = db.scalar(select(Course).where(Course.source_id == source.id, Course.code == code))
    if not course:
        course = Course(source_id=source.id, code=code, title=title[:500], subject=cand.subject,
                        university=cand.university or source.university, url=cand.course_url or source.url,
                        description=cand.course_description, instructors=cand.instructors, term=cand.term,
                        license=cand.license or source.license)
        db.add(course)
        db.flush()
    elif title and course.title.lower() in ("", code.lower()) and title.lower() != code.lower():
        course.title = title[:500]
    return course


def save_file(source: Source, data: bytes, fmt: str, checksum: str) -> str:
    d = get_settings().data_path / "files" / source.key
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{checksum[:20]}.{fmt if fmt != 'md' else 'md'}"
    if not p.exists():
        p.write_bytes(data)
    return str(p.relative_to(get_settings().data_path))


def build_flashcards(db: Session, doc: Document, use_ai: bool = False, max_cards: int = 40) -> int:
    """(Re)generate flashcards. Cards that already have evaluations are kept untouched."""
    kept = []
    for c in list(doc.flashcards):
        if c.evaluations:
            kept.append(c)
        else:
            db.delete(c)
    db.flush()
    kept_q = {re.sub(r"[^a-z0-9]+", "", c.question.lower()) for c in kept}

    cards = []
    generator = "rules"
    if use_ai and get_settings().ai_enabled:
        cards = ai.generate_ai_cards(doc.text, doc.sections, max_cards=max_cards)
        generator = f"ai:{ai.model_name()}"
    if not cards:
        cards = generate_cards(doc.text, doc.sections, max_cards=max_cards)
        generator = "rules"

    topic_ids = [dt.topic_id for dt in sorted(doc.topics, key=lambda d: -d.score)]
    topics = list(db.scalars(select(Topic).where(Topic.id.in_(topic_ids))).all()) if topic_ids else []
    fallback = next((t for t in topics if t.id == topic_ids[0]), None) if topic_ids else None
    n = 0
    for c in cards:
        if c.key() in kept_q:
            continue
        sec = doc.sections[c.section_index] if 0 <= c.section_index < len(doc.sections) else {}
        topic = best_topic_for_text(c.question + " " + c.answer, topics) or fallback
        db.add(Flashcard(
            document_id=doc.id, category=doc.category, subject=doc.subject, card_type=c.card_type,
            question=c.question, answer=c.answer, excerpt=doc.text[c.start:c.end][:3000],
            section_index=c.section_index, section_title=sec.get("title", ""), page=sec.get("page"),
            char_start=c.start, char_end=c.end, topic_id=topic.id if topic else None,
            generator=generator, confidence=c.confidence,
        ))
        n += 1
    db.flush()
    return n


def process_document_content(db: Session, doc: Document, data: bytes, cand: Candidate, source: Source,
                             options: dict) -> None:
    fmt = cand.fmt or detect_format(cand.file_url or cand.url, "", data)
    if fmt == "pdf" and not data.startswith(b"%PDF"):
        fmt = detect_format(cand.url, "", data)
        if fmt == "pdf":
            fmt = "html"
    checksum = hashlib.sha256(data).hexdigest()
    dup = db.scalar(select(Document).where(Document.checksum == checksum, Document.id != doc.id,
                                           Document.status == "collected"))
    if dup:
        raise SkipDocument(f"duplicate of document #{dup.id}")
    local = Path(cand.local_file) if cand.local_file else None
    root = Path(cand.repo_root) if cand.repo_root else None
    ex = extract(data, fmt, local, root, title=cand.title)
    if ex.word_count < MIN_WORDS:
        raise SkipDocument(f"too little extractable text ({ex.word_count} words)")

    title = cand.title if _good_title(cand.title) and fmt in ("pdf",) and source.category == "mit" else ""
    title = title or (ex.title if _good_title(ex.title) else "") or cand.title or Path(cand.url).stem
    course = upsert_course(db, source, cand, doc_title=title)

    doc.title = title[:500]
    doc.course_id = course.id
    doc.subject = cand.subject
    doc.category = source.category
    doc.format = fmt
    doc.file_url = cand.file_url
    doc.author = (ex.author if _good_author(ex.author) else "") or cand.author or source.author
    doc.license = cand.license or source.license
    doc.text = ex.text
    doc.sections = ex.sections
    doc.summary = ex.summary()
    doc.word_count = ex.word_count
    doc.page_count = ex.page_count
    doc.checksum = checksum
    doc.local_path = save_file(source, data, fmt, checksum)
    doc.meta = {**(doc.meta or {}), **ex.meta, "terms": top_terms(ex.text), "candidate": cand.to_meta()}
    doc.status = "collected"
    doc.error = ""
    db.flush()
    assign_topics(db, doc)
    db.refresh(doc)
    if options.get("generate_flashcards", True):
        build_flashcards(db, doc, use_ai=options.get("use_ai", False), max_cards=int(options.get("max_cards", 40)))


def process_candidate(db: Session, source: Source, cand: Candidate, fetcher: Fetcher, job_id: int | None,
                      options: dict) -> tuple[str, str]:
    """Returns (status, message) where status is 'collected', 'skipped' or 'failed'."""
    doc = db.scalar(select(Document).where(Document.url == cand.url, Document.source_id == source.id))
    if doc and doc.status == "collected" and not options.get("force"):
        return "skipped", "already collected"
    is_new = doc is None
    if is_new:
        doc = Document(source_id=source.id, category=source.category, subject=cand.subject,
                       title=(cand.title or cand.url)[:500], url=cand.url, file_url=cand.file_url,
                       author=cand.author, license=cand.license, meta={"candidate": cand.to_meta()})
        db.add(doc)
        db.flush()
    doc.job_id = job_id
    doc.attempts = (doc.attempts or 0) + 1
    try:
        if cand.meta.get("course_page"):
            raise RuntimeError(cand.meta.get("error_hint", "course page unavailable"))
        if cand.data is not None:
            data = cand.data
        elif cand.local_file and Path(cand.local_file).is_file():
            data = Path(cand.local_file).read_bytes()
        else:
            data = fetcher.get(cand.file_url or cand.url).content
        process_document_content(db, doc, data, cand, source, options)
        db.commit()
        n_cards = db.scalar(select(func.count(Flashcard.id)).where(Flashcard.document_id == doc.id))
        return "collected", f"{doc.word_count} words, {n_cards} flashcards"
    except SkipDocument as e:
        db.rollback()
        stale = db.scalar(select(Document).where(Document.url == cand.url, Document.source_id == source.id,
                                                 Document.status != "collected"))
        if stale:
            db.delete(stale)
        db.commit()
        return "skipped", str(e)
    except Exception as e:  # noqa: BLE001 - we record any failure for retry
        db.rollback()
        doc = db.scalar(select(Document).where(Document.url == cand.url, Document.source_id == source.id))
        if doc is None:
            doc = Document(source_id=source.id, category=source.category, subject=cand.subject,
                           title=(cand.title or cand.url)[:500], url=cand.url, file_url=cand.file_url,
                           author=cand.author, license=cand.license, attempts=1)
            db.add(doc)
        doc.meta = {**(doc.meta or {}), "candidate": cand.to_meta()}
        if doc.status != "collected":
            doc.status = "failed"
        doc.error = f"{type(e).__name__}: {e}"[:2000]
        doc.job_id = job_id
        db.commit()
        return "failed", doc.error
