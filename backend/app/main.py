from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import Base, SessionLocal, engine
from .jobs import mark_interrupted_jobs
from .routers import admin, catalog, documents, flashcards, stats, topics
from .seed import seed


def init_db() -> None:
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    mark_interrupted_jobs()
    yield


app = FastAPI(title="Lecture Notes & Flashcards API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in get_settings().cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"ok": True}


for r in (catalog, documents, topics, flashcards, stats, admin):
    app.include_router(r.router)
