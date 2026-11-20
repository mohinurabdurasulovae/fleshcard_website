"""Background collection jobs (threaded inside the API process, or synchronous from the CLI)."""

from __future__ import annotations

import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from sqlalchemy import select

from .collectors import COLLECTORS
from .collectors.base import Candidate, Fetcher
from .config import get_settings
from .db import SessionLocal
from .models import CollectionJob, Document, Source
from .pipeline import build_flashcards, process_candidate

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="collector")


def _now():
    return datetime.now(timezone.utc)


class JobLogger:
    def __init__(self, db, job: CollectionJob, echo: bool = False):
        self.db, self.job, self.echo = db, job, echo

    def __call__(self, msg: str) -> None:
        line = f"{_now().strftime('%H:%M:%S')}  {msg}"
        if self.echo:
            print(line, flush=True)
        log = list(self.job.log or [])
        log.append(line)
        self.job.log = log[-600:]
        self.db.commit()


def create_job(db, kind: str, subjects: list[str], source_keys: list[str], options: dict) -> CollectionJob:
    job = CollectionJob(kind=kind, subjects=subjects, source_keys=source_keys, options=options, status="queued", log=[])
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def submit(job_id: int) -> None:
    _executor.submit(run_job, job_id)


def _cancelled(db, job: CollectionJob) -> bool:
    db.refresh(job, ["cancel_requested"])
    return bool(job.cancel_requested)


def run_job(job_id: int, echo: bool = False) -> None:
    db = SessionLocal()
    job = db.get(CollectionJob, job_id)
    if not job:
        db.close()
        return
    log = JobLogger(db, job, echo)
    job.status, job.started_at = "running", _now()
    db.commit()
    settings = get_settings()
    fetcher = Fetcher(settings, log)
    try:
        if job.kind == "collect":
            _run_collect(db, job, fetcher, log)
        elif job.kind == "retry":
            _run_retry(db, job, fetcher, log)
        elif job.kind == "regenerate":
            _run_regenerate(db, job, log)
        job.status = "cancelled" if job.cancel_requested else "completed"
        log(f"Finished: {job.succeeded} collected, {job.skipped} skipped, {job.failed} failed")
    except Exception as e:  # noqa: BLE001
        db.rollback()
        job.status = "failed"
        log(f"Job failed: {e}")
        log(traceback.format_exc()[-1500:])
    finally:
        job.finished_at = _now()
        job.current = ""
        db.commit()
        db.close()


def _tally(db, job, status: str, msg: str, title: str, log) -> None:
    job.processed += 1
    if status == "collected":
        job.succeeded += 1
        log(f"  ✓ {title[:90]} — {msg}")
    elif status == "skipped":
        job.skipped += 1
        log(f"  · skipped {title[:80]} ({msg[:120]})")
    else:
        job.failed += 1
        log(f"  ✗ {title[:80]} — {msg[:200]}")
    db.commit()


def _run_collect(db, job: CollectionJob, fetcher: Fetcher, log) -> None:
    opts = job.options or {}
    keys = job.source_keys or [s.key for s in db.scalars(select(Source).where(Source.enabled.is_(True))).all()]
    subjects = job.subjects or []
    max_per_source = int(opts.get("max_docs_per_source") or 0)

    # phase 1: discovery
    plan: list[tuple[Source, list[Candidate]]] = []
    for key in keys:
        source = db.scalar(select(Source).where(Source.key == key))
        if not source:
            log(f"Unknown source '{key}'")
            continue
        subs = [s for s in (subjects or source.subjects) if s in (source.subjects or [])]
        if not subs:
            continue
        log(f"Discovering · {source.name} ({', '.join(subs)})")
        job.current = f"Discovering {source.name}"
        db.commit()
        collector = COLLECTORS[source.kind](source, get_settings(), fetcher, log, subs, opts, db=db)
        found: list[Candidate] = []
        try:
            for cand in collector.candidates():
                found.append(cand)
                if max_per_source and len(found) >= max_per_source:
                    break
                if _cancelled(db, job):
                    return
        except Exception as e:  # noqa: BLE001
            log(f"  ✗ discovery failed for {source.name}: {type(e).__name__}: {e}")
            job.failed += 1
        log(f"  found {len(found)} candidate documents")
        job.total += len(found)
        db.commit()
        plan.append((source, found))

    # phase 2: download + process
    for source, cands in plan:
        for cand in cands:
            if _cancelled(db, job):
                log("Cancellation requested – stopping")
                return
            job.current = cand.title or cand.url
            db.commit()
            status, msg = process_candidate(db, source, cand, fetcher, job.id, opts)
            _tally(db, job, status, msg, cand.title or cand.url, log)


def _run_retry(db, job: CollectionJob, fetcher: Fetcher, log) -> None:
    opts = job.options or {}
    ids = opts.get("document_ids")
    q = select(Document).where(Document.status == "failed")
    if ids:
        q = q.where(Document.id.in_(ids))
    docs = db.scalars(q).all()
    job.total = len(docs)
    db.commit()
    log(f"Retrying {len(docs)} failed documents")
    for d in docs:
        if _cancelled(db, job):
            return
        source = d.source
        cand_meta = (d.meta or {}).get("candidate")
        if not cand_meta:
            cand = Candidate(url=d.url, file_url=d.file_url, title=d.title, subject=d.subject,
                             author=d.author, license=d.license)
        else:
            cand = Candidate.from_meta(cand_meta)
        job.current = d.title
        db.commit()
        if cand.meta.get("course_page"):
            # re-run the MIT collector for just this course
            from .models import Course
            course = db.scalar(select(Course).where(Course.source_id == source.id, Course.code == cand.course_code))
            if course:
                collector = COLLECTORS[source.kind](source, get_settings(), fetcher, log, [course.subject],
                                                    {**opts, "course_ids": [course.id], "discover": False}, db=db)
                try:
                    found = [c for c in collector.candidates() if not c.meta.get("course_page")]
                except Exception as e:  # noqa: BLE001
                    found = []
                    log(f"  ✗ {course.code}: {e}")
                ok = 0
                for c in found:
                    st, msg = process_candidate(db, source, c, fetcher, job.id, opts)
                    ok += st == "collected"
                    log(f"    {st}: {c.title[:80]}")
                if ok:
                    db.delete(db.get(Document, d.id))
                    db.commit()
                _tally(db, job, "collected" if ok else "failed", f"{ok} documents" if ok else "still unavailable",
                       d.title, log)
                continue
        status, msg = process_candidate(db, source, cand, fetcher, job.id, {**opts, "force": True})
        _tally(db, job, status, msg, d.title, log)


def _run_regenerate(db, job: CollectionJob, log) -> None:
    opts = job.options or {}
    ids = opts.get("document_ids")
    q = select(Document).where(Document.status == "collected")
    if ids:
        q = q.where(Document.id.in_(ids))
    docs = db.scalars(q).all()
    job.total = len(docs)
    db.commit()
    for d in docs:
        if _cancelled(db, job):
            return
        job.current = d.title
        try:
            n = build_flashcards(db, d, use_ai=opts.get("use_ai", False), max_cards=int(opts.get("max_cards", 40)))
            db.commit()
            _tally(db, job, "collected", f"{n} new flashcards", d.title, log)
        except Exception as e:  # noqa: BLE001
            db.rollback()
            _tally(db, job, "failed", str(e), d.title, log)


def mark_interrupted_jobs() -> None:
    db = SessionLocal()
    try:
        for j in db.scalars(select(CollectionJob).where(CollectionJob.status.in_(["running", "queued"]))).all():
            j.status = "failed"
            j.log = list(j.log or []) + ["Interrupted: the API restarted while this job was running. Start it again."]
            j.finished_at = _now()
        db.commit()
    finally:
        db.close()
