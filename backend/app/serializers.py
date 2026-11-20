from .criteria import level_to_score
from .models import CollectionJob, Course, Document, Evaluation, Flashcard, Source, Topic


def iso(dt):
    return dt.isoformat() if dt else None


def source_out(s: Source) -> dict:
    return {"id": s.id, "key": s.key, "name": s.name, "category": s.category, "kind": s.kind, "url": s.url,
            "subjects": s.subjects, "university": s.university, "author": s.author, "license": s.license,
            "description": s.description, "enabled": s.enabled}


def course_out(c: Course, doc_count: int | None = None, card_count: int | None = None) -> dict:
    return {"id": c.id, "code": c.code, "title": c.title, "subject": c.subject, "university": c.university,
            "url": c.url, "description": c.description, "instructors": c.instructors, "term": c.term,
            "license": c.license, "source": {"id": c.source.id, "key": c.source.key, "name": c.source.name,
                                             "category": c.source.category},
            "category": c.source.category, "document_count": doc_count, "flashcard_count": card_count,
            "created_at": iso(c.created_at)}


def doc_brief(d: Document, card_count: int | None = None) -> dict:
    return {"id": d.id, "title": d.title, "subject": d.subject, "category": d.category, "format": d.format,
            "url": d.url, "file_url": d.file_url, "author": d.author, "license": d.license, "summary": d.summary,
            "word_count": d.word_count, "page_count": d.page_count, "status": d.status,
            "review_status": d.review_status, "error": d.error, "attempts": d.attempts,
            "has_file": bool(d.local_path),
            "source": {"id": d.source.id, "key": d.source.key, "name": d.source.name} if d.source else None,
            "course": {"id": d.course.id, "code": d.course.code, "title": d.course.title,
                       "university": d.course.university} if d.course else None,
            "topics": [{"id": dt.topic.id, "slug": dt.topic.slug, "name": dt.topic.name, "score": dt.score}
                       for dt in sorted(d.topics, key=lambda x: -x.score)[:5]],
            "flashcard_count": card_count, "created_at": iso(d.created_at)}


def topic_out(t: Topic, **extra) -> dict:
    return {"id": t.id, "slug": t.slug, "name": t.name, "subject": t.subject, "description": t.description,
            "keywords": t.keywords, **extra}


def eval_summary(evals: list[Evaluation]) -> dict:
    if not evals:
        return {"count": 0, "mean_score": None}
    return {"count": len(evals), "mean_score": round(sum(level_to_score(e.overall) for e in evals) / len(evals), 2)}


def card_out(c: Flashcard, with_evals: bool = True) -> dict:
    d = c.document
    sec = None
    out = {"id": c.id, "document_id": c.document_id, "category": c.category, "subject": c.subject,
           "card_type": c.card_type, "question": c.question, "answer": c.answer, "excerpt": c.excerpt,
           "section_index": c.section_index, "section_title": c.section_title, "page": c.page,
           "char_start": c.char_start, "char_end": c.char_end, "generator": c.generator,
           "confidence": c.confidence,
           "topic": {"id": c.topic.id, "slug": c.topic.slug, "name": c.topic.name} if c.topic else None,
           "document": {"id": d.id, "title": d.title, "url": d.url, "format": d.format, "author": d.author,
                        "license": d.license, "source": d.source.name if d.source else "",
                        "course": f"{d.course.code} · {d.course.title}" if d.course else "",
                        "university": d.course.university if d.course else "",
                        "katex_macros": (d.meta or {}).get("katex_macros", {})},
           "created_at": iso(c.created_at)}
    if with_evals:
        out["evaluations"] = eval_summary(c.evaluations)
    del sec
    return out


def eval_out(e: Evaluation) -> dict:
    return {"id": e.id, "flashcard_id": e.flashcard_id, "overall": e.overall, "criteria": e.criteria,
            "comment": e.comment, "evaluator": e.evaluator, "created_at": iso(e.created_at)}


def job_out(j: CollectionJob, with_log: bool = False) -> dict:
    pct = 100 if j.status in ("completed",) else (round(100 * j.processed / j.total) if j.total else 0)
    out = {"id": j.id, "status": j.status, "kind": j.kind, "subjects": j.subjects, "source_keys": j.source_keys,
           "options": j.options, "total": j.total, "processed": j.processed, "succeeded": j.succeeded,
           "failed": j.failed, "skipped": j.skipped, "current": j.current, "progress": pct,
           "created_at": iso(j.created_at), "started_at": iso(j.started_at), "finished_at": iso(j.finished_at),
           "log_tail": (j.log or [])[-6:]}
    if with_log:
        out["log"] = j.log or []
    return out
