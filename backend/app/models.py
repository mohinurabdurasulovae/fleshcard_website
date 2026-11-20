from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def now() -> datetime:
    return datetime.now(timezone.utc)


class Source(Base):
    """A place notes come from: MIT OCW or a student-created website / repository."""

    __tablename__ = "sources"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(20), index=True)  # mit | student
    kind: Mapped[str] = mapped_column(String(30))  # mit_ocw | github | website | pdf
    url: Mapped[str] = mapped_column(String(1000))
    subjects: Mapped[list] = mapped_column(JSON, default=list)
    university: Mapped[str] = mapped_column(String(255), default="")
    author: Mapped[str] = mapped_column(String(255), default="")
    license: Mapped[str] = mapped_column(String(500), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    courses: Mapped[list["Course"]] = relationship(back_populates="source")


class Course(Base):
    __tablename__ = "courses"
    __table_args__ = (UniqueConstraint("source_id", "code", name="uq_course_source_code"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(500))
    subject: Mapped[str] = mapped_column(String(50), index=True)
    university: Mapped[str] = mapped_column(String(255), default="")
    url: Mapped[str] = mapped_column(String(1000), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    instructors: Mapped[str] = mapped_column(String(500), default="")
    term: Mapped[str] = mapped_column(String(100), default="")
    level: Mapped[str] = mapped_column(String(50), default="")
    license: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    source: Mapped[Source] = relationship(back_populates="courses")
    documents: Mapped[list["Document"]] = relationship(back_populates="course")


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), index=True)
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id", ondelete="SET NULL"), index=True, nullable=True)
    category: Mapped[str] = mapped_column(String(20), index=True)  # mit | student (denormalised)
    subject: Mapped[str] = mapped_column(String(50), index=True)
    title: Mapped[str] = mapped_column(String(500))
    url: Mapped[str] = mapped_column(String(1000), index=True)  # original public location
    file_url: Mapped[str] = mapped_column(String(1000), default="")  # direct download link
    format: Mapped[str] = mapped_column(String(20), default="")  # pdf | html | md | tex
    author: Mapped[str] = mapped_column(String(500), default="")
    license: Mapped[str] = mapped_column(String(500), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    sections: Mapped[list] = mapped_column(JSON, default=list)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    local_path: Mapped[str] = mapped_column(String(1000), default="")
    checksum: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)  # pending|collected|failed
    review_status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|approved|rejected
    error: Mapped[str] = mapped_column(Text, default="")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    job_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)

    source: Mapped[Source] = relationship()
    course: Mapped[Course | None] = relationship(back_populates="documents")
    topics: Mapped[list["DocumentTopic"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    flashcards: Mapped[list["Flashcard"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class Topic(Base):
    __tablename__ = "topics"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(50), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    keywords: Mapped[list] = mapped_column(JSON, default=list)

    documents: Mapped[list["DocumentTopic"]] = relationship(back_populates="topic", cascade="all, delete-orphan")


class DocumentTopic(Base):
    __tablename__ = "document_topics"
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True)
    score: Mapped[float] = mapped_column(Float, default=0)
    hits: Mapped[int] = mapped_column(Integer, default=0)
    sections: Mapped[list] = mapped_column(JSON, default=list)  # indices of sections covering the topic

    document: Mapped[Document] = relationship(back_populates="topics")
    topic: Mapped[Topic] = relationship(back_populates="documents")


class Flashcard(Base):
    __tablename__ = "flashcards"
    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(20), index=True)  # mit | student
    subject: Mapped[str] = mapped_column(String(50), index=True)
    card_type: Mapped[str] = mapped_column(String(20), index=True)  # definition|concept|explanation|formula|comparison
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    excerpt: Mapped[str] = mapped_column(Text, default="")
    section_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section_title: Mapped[str] = mapped_column(String(500), default="")
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    char_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    char_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    generator: Mapped[str] = mapped_column(String(80), default="rules")
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    document: Mapped[Document] = relationship(back_populates="flashcards")
    topic: Mapped[Topic | None] = relationship()
    evaluations: Mapped[list["Evaluation"]] = relationship(back_populates="flashcard", cascade="all, delete-orphan")


class Evaluation(Base):
    __tablename__ = "evaluations"
    id: Mapped[int] = mapped_column(primary_key=True)
    flashcard_id: Mapped[int] = mapped_column(ForeignKey("flashcards.id", ondelete="CASCADE"), index=True)
    overall: Mapped[int] = mapped_column(Integer)  # 1 Excellent … 5 Unacceptable
    criteria: Mapped[dict] = mapped_column(JSON, default=dict)  # {criterion_key: 1..5}
    comment: Mapped[str] = mapped_column(Text, default="")
    evaluator: Mapped[str] = mapped_column(String(120), default="anonymous")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)

    flashcard: Mapped[Flashcard] = relationship(back_populates="evaluations")


class CollectionJob(Base):
    __tablename__ = "collection_jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)  # queued|running|completed|failed|cancelled
    kind: Mapped[str] = mapped_column(String(20), default="collect")  # collect | retry | regenerate
    subjects: Mapped[list] = mapped_column(JSON, default=list)
    source_keys: Mapped[list] = mapped_column(JSON, default=list)
    options: Mapped[dict] = mapped_column(JSON, default=dict)
    total: Mapped[int] = mapped_column(Integer, default=0)
    processed: Mapped[int] = mapped_column(Integer, default=0)
    succeeded: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)
    skipped: Mapped[int] = mapped_column(Integer, default=0)
    current: Mapped[str] = mapped_column(String(1000), default="")
    log: Mapped[list] = mapped_column(JSON, default=list)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
