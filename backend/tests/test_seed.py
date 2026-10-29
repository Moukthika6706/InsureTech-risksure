"""The seed script, run against an isolated in-memory database."""
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app import seed as seed_module
from app.lifecycle import STATUSES
from app.models import AuditEvent, Policy, Quote


@pytest.fixture
def seeded(db_session, monkeypatch):
    monkeypatch.setattr(seed_module, "SessionLocal", db_session)
    monkeypatch.setattr(seed_module, "engine", db_session.kw["bind"])
    summary = seed_module.seed(count=40, verbose=False)
    return db_session, summary


def test_seed_creates_the_requested_book(seeded):
    Session, summary = seeded
    assert summary["quotes"] == 40
    assert {p["product"] for p in summary["by_product"]} == {"auto", "home", "business"}
    with Session() as db:
        quotes = db.scalars(select(Quote)).all()
        assert all(q.status in STATUSES and q.status != "draft" for q in quotes)
        assert all(q.applicant.source == "sample" and q.applicant.external_ref for q in quotes)


def test_seeded_history_is_consistent(seeded):
    Session, _ = seeded
    with Session() as db:
        for q in db.scalars(select(Quote)):
            events = db.scalars(select(AuditEvent).where(AuditEvent.quote_id == q.id).order_by(AuditEvent.id)).all()
            assert [e.action for e in events[:2]] == ["create", "rate"]
            assert events[-1].to_status == q.status                       # audit trail agrees with the quote
            times = [e.created_at for e in events]
            assert times == sorted(times)                                  # time moves forward
            assert times[-1].replace(tzinfo=None) <= datetime.now(timezone.utc).replace(tzinfo=None)   # never in the future
        for p in db.scalars(select(Policy)):
            assert p.quote.status == "issued" and p.policy_number.startswith("P-")


def test_seed_refuses_to_mix_with_existing_data(seeded, monkeypatch):
    with pytest.raises(SystemExit):
        seed_module.seed(count=5, verbose=False)
    assert seed_module.seed_if_empty() is None                            # startup hook leaves data alone


def test_reset_replaces_the_book(seeded):
    Session, _ = seeded
    assert seed_module.seed(count=10, reset=True, verbose=False)["quotes"] == 10
