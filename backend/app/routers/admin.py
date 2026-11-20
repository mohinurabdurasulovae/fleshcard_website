from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..jobs import create_job, submit
from ..models import CollectionJob, Document, Source
from ..seed import SUBJECTS
from ..serializers import job_out, source_out

router = APIRouter(prefix="/api/admin", tags=["admin"])


class JobIn(BaseModel):
    subjects: list[str] = []
    source_keys: list[str] = []
    max_docs_per_source: int = 0
    max_docs_per_course: int = 8
    generate_flashcards: bool = True
    use_ai: bool = False
    force: bool = False
    discover: bool = True


@router.get("/summary")
def summary(db: Session = Depends(get_db)):
    status = dict(db.execute(select(Document.status, func.count()).group_by(Document.status)).all())
    review = dict(db.execute(select(Document.review_status, func.count()).where(Document.status == "collected")
                             .group_by(Document.review_status)).all())
    running = db.scalar(select(func.count()).select_from(CollectionJob).where(CollectionJob.status.in_(["running", "queued"])))
    s = get_settings()
    return {"status": status, "review": review, "running_jobs": running,
            "ai": {"enabled": s.ai_enabled, "provider": s.ai_provider},
            "database": s.database_url.split("://")[0], "subjects": SUBJECTS}


@router.get("/jobs")
def jobs(limit: int = 20, db: Session = Depends(get_db)):
    return [job_out(j) for j in db.scalars(select(CollectionJob).order_by(CollectionJob.id.desc()).limit(limit)).all()]


@router.get("/jobs/{job_id}")
def job(job_id: int, db: Session = Depends(get_db)):
    j = db.get(CollectionJob, job_id)
    if not j:
        raise HTTPException(404)
    return job_out(j, with_log=True)


@router.post("/jobs")
def start_job(body: JobIn, db: Session = Depends(get_db)):
    subjects = [s for s in body.subjects if s in SUBJECTS] or SUBJECTS
    keys = body.source_keys
    if not keys:
        keys = [s.key for s in db.scalars(select(Source).where(Source.enabled.is_(True), Source.kind != "upload")).all()]
    if body.use_ai and not get_settings().ai_enabled:
        raise HTTPException(400, "AI generation is not configured on the server")
    opts = body.model_dump(exclude={"subjects", "source_keys"})
    j = create_job(db, "collect", subjects, keys, opts)
    submit(j.id)
    return job_out(j)


@router.post("/jobs/{job_id}/cancel")
def cancel(job_id: int, db: Session = Depends(get_db)):
    j = db.get(CollectionJob, job_id)
    if not j:
        raise HTTPException(404)
    j.cancel_requested = True
    db.commit()
    return job_out(j)


class IdsIn(BaseModel):
    document_ids: list[int] = []
    use_ai: bool = False


@router.post("/retry-failed")
def retry_failed(body: IdsIn, db: Session = Depends(get_db)):
    j = create_job(db, "retry", [], [], {"document_ids": body.document_ids, "generate_flashcards": True})
    submit(j.id)
    return job_out(j)


@router.post("/regenerate")
def regenerate(body: IdsIn, db: Session = Depends(get_db)):
    if body.use_ai and not get_settings().ai_enabled:
        raise HTTPException(400, "AI generation is not configured on the server")
    j = create_job(db, "regenerate", [], [], {"document_ids": body.document_ids, "use_ai": body.use_ai})
    submit(j.id)
    return job_out(j)


class SourcePatch(BaseModel):
    enabled: bool | None = None


@router.patch("/sources/{key}")
def patch_source(key: str, body: SourcePatch, db: Session = Depends(get_db)):
    s = db.scalar(select(Source).where(Source.key == key))
    if not s:
        raise HTTPException(404)
    if body.enabled is not None:
        s.enabled = body.enabled
    db.commit()
    return source_out(s)
