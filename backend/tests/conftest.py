"""Shared fixtures: an isolated in-memory database and an API client using it."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app


@pytest.fixture
def db_session():
    """A fresh in-memory database per test (StaticPool = one shared connection)."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    yield Session
    engine.dispose()


@pytest.fixture
def client(db_session):
    def override():
        db = db_session()
        try:
            yield db
        finally:
            db.close()
    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.clear()
