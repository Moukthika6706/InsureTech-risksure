"""Database tables. Product definitions are NOT here — they live in config/*.yaml."""
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.types import TypeDecorator
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def now() -> datetime:
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    """A timestamp that always comes back as UTC. SQLite stores no time zone, so
    without this the API would send "18:23" and browsers would read it as local time."""
    impl = DateTime
    cache_ok = True

    def process_result_value(self, value, dialect):
        return value.replace(tzinfo=timezone.utc) if value is not None and value.tzinfo is None else value


class Applicant(Base):
    """The person or business asking for cover, with the form answers as JSON."""
    __tablename__ = "applicants"
    id: Mapped[int] = mapped_column(primary_key=True)
    product: Mapped[str] = mapped_column(String(32), index=True)
    data: Mapped[dict] = mapped_column(JSON)
    source: Mapped[str] = mapped_column(String(16), default="manual")    # manual | sample
    external_ref: Mapped[Optional[str]] = mapped_column(String(32))       # e.g. AUT-00042 from the CSV
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=now)


class Quote(Base):
    """A priced offer. Its status moves through the lifecycle in app/lifecycle.py."""
    __tablename__ = "quotes"
    id: Mapped[int] = mapped_column(primary_key=True)
    quote_number: Mapped[Optional[str]] = mapped_column(String(32), unique=True)
    product: Mapped[str] = mapped_column(String(32), index=True)
    product_version: Mapped[str] = mapped_column(String(16))
    applicant_id: Mapped[int] = mapped_column(ForeignKey("applicants.id"))
    status: Mapped[str] = mapped_column(String(16), index=True, default="draft")
    decision: Mapped[Optional[str]] = mapped_column(String(24))
    coverages: Mapped[list] = mapped_column(JSON, default=list)
    base_premium: Mapped[Optional[float]] = mapped_column(Float)
    rated_premium: Mapped[Optional[float]] = mapped_column(Float)     # after rating factors
    premium: Mapped[Optional[float]] = mapped_column(Float)           # after underwriting loads
    override_premium: Mapped[Optional[float]] = mapped_column(Float)  # set by an underwriter
    total_load_pct: Mapped[float] = mapped_column(Float, default=0)
    breakdown: Mapped[list] = mapped_column(JSON, default=list)       # waterfall steps
    risk: Mapped[dict] = mapped_column(JSON, default=dict)            # score, band, top factors
    rule_hits: Mapped[list] = mapped_column(JSON, default=list)
    underwriter_note: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=now, onupdate=now)

    applicant: Mapped[Applicant] = relationship()
    events: Mapped[list["AuditEvent"]] = relationship(back_populates="quote", order_by="AuditEvent.id")
    policy: Mapped[Optional["Policy"]] = relationship(back_populates="quote")

    @property
    def final_premium(self) -> Optional[float]:
        """What the customer pays: the underwriter's override if there is one."""
        return self.override_premium if self.override_premium is not None else self.premium


class Policy(Base):
    """An issued policy: the contract created when a bound quote is issued."""
    __tablename__ = "policies"
    id: Mapped[int] = mapped_column(primary_key=True)
    policy_number: Mapped[str] = mapped_column(String(32), unique=True)
    quote_id: Mapped[int] = mapped_column(ForeignKey("quotes.id"), unique=True)
    product: Mapped[str] = mapped_column(String(32), index=True)
    premium: Mapped[float] = mapped_column(Float)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    issued_at: Mapped[datetime] = mapped_column(UTCDateTime, default=now)

    quote: Mapped[Quote] = relationship(back_populates="policy")


class AuditEvent(Base):
    """One row per state change: who did what, when, and why. Never updated or deleted."""
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    quote_id: Mapped[int] = mapped_column(ForeignKey("quotes.id"), index=True)
    action: Mapped[str] = mapped_column(String(32))
    from_status: Mapped[Optional[str]] = mapped_column(String(16))
    to_status: Mapped[str] = mapped_column(String(16))
    actor: Mapped[str] = mapped_column(String(64))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=now)

    quote: Mapped[Quote] = relationship(back_populates="events")


class PublishedRule(Base):
    """A rule approved through the rule assistant (Step 7). Stored here, not in
    rules.yaml, because the server's disk is wiped on every redeploy."""
    __tablename__ = "published_rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    rule_id: Mapped[str] = mapped_column(String(64), unique=True)
    product: Mapped[str] = mapped_column(String(32))
    rule: Mapped[dict] = mapped_column(JSON)
    source_text: Mapped[Optional[str]] = mapped_column(Text)        # the underwriter's English
    published_by: Mapped[str] = mapped_column(String(64))
    published_at: Mapped[datetime] = mapped_column(UTCDateTime, default=now)
    enabled: Mapped[bool] = mapped_column(default=True)
