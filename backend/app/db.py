from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import get_settings

settings = get_settings()
_url = settings.database_url
_kwargs: dict = {"pool_pre_ping": True, "connect_args": {"connect_timeout": 10}}
if _url.startswith("sqlite"):
    if _url.startswith("sqlite:///./"):
        _url = "sqlite:///" + str(settings.data_path.parent / _url[len("sqlite:///./"):])
    _kwargs = {"connect_args": {"check_same_thread": False}}

engine = create_engine(_url, **_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
