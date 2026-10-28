"""Database connection. SQLite by default; set DATABASE_URL to use another database."""
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DEFAULT_URL = f"sqlite:///{Path(__file__).resolve().parents[1] / 'risksure.db'}"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_URL)

# check_same_thread=False: FastAPI may use a session from a different thread than created it.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False}
                       if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency: one session per request, always closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
