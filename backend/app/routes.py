"""REST endpoints. Each handler is thin: validate input, call services/engine, shape output."""
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app import services
from app.db import get_db
from app.lifecycle import STATUSES
from app.models import AuditEvent, Policy, Quote
from app.schemas import (ActorRequest, AuditEventOut, IssueRequest, PolicyOut, QuoteDetail,
                         QuoteRequest, QuoteSummary, UnderwriteRequest)
from engine.config import get_product, load_products
from engine.quote import run_quote

router = APIRouter()
Status = Literal[tuple(STATUSES)]   # lets /docs show the allowed values


def _product(code: str):
    try:
        return get_product(code)
    except KeyError as e:
        raise HTTPException(404, str(e).strip("'\""))


def _quote(db: Session, quote_id: int) -> Quote:
    q = db.get(Quote, quote_id)
    if q is None:
        raise HTTPException(404, f"Quote {quote_id} not found")
    return q


def _summary(q: Quote) -> QuoteSummary:
    return QuoteSummary.model_validate(q).model_copy(update=services.summary(q))


def _detail(q: Quote) -> QuoteDetail:
    return QuoteDetail.model_validate(
        {**QuoteSummary.model_validate(q).model_dump(), **services.summary(q),
         **{k: getattr(q, k) for k in ("product_version", "applicant_id", "coverages", "base_premium",
                                       "rated_premium", "total_load_pct", "breakdown", "risk",
                                       "underwriter_note")},
         "applicant": q.applicant.data,
         "policy": PolicyOut.model_validate(q.policy) if q.policy else None,
         "events": [AuditEventOut.model_validate(e) for e in q.events]})


# ------------------------------------------------------------- products

@router.get("/products", tags=["products"])
def list_products():
    return [{"code": p.code, "name": p.name, "description": p.description, "version": p.version,
             "risk_method": p.risk["method"]} for p in load_products().values()]


@router.get("/products/{code}", tags=["products"])
def product_detail(code: str):
    """Full product config — the frontend builds its quote form from `fields`."""
    return _product(code).model_dump()


# ---------------------------------------------------------------- rating

@router.post("/rate", tags=["quotes"])
def rate_only(req: QuoteRequest, db: Session = Depends(get_db)):
    """Price + risk + decision without saving anything (used by the what-if simulator)."""
    _product(req.product)
    return run_quote(req.product, req.applicant, req.coverages, rules=services.active_rules(db))


# ---------------------------------------------------------------- quotes

@router.post("/quotes", response_model=QuoteDetail, status_code=201, tags=["quotes"])
def create_quote(req: QuoteRequest, db: Session = Depends(get_db)):
    _product(req.product)
    q = services.create_quote(db, req.product, req.applicant, req.coverages, req.actor)
    return _detail(q)


@router.get("/quotes", response_model=list[QuoteSummary], tags=["quotes"])
def list_quotes(status: Optional[Status] = None, product: Optional[str] = None,
                limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0),
                db: Session = Depends(get_db)):
    stmt = select(Quote).order_by(Quote.id.desc()).limit(limit).offset(offset)
    if status:
        stmt = stmt.where(Quote.status == status)
    if product:
        stmt = stmt.where(Quote.product == product)
    return [_summary(q) for q in db.scalars(stmt)]


@router.get("/quotes/{quote_id}", response_model=QuoteDetail, tags=["quotes"])
def get_quote(quote_id: int, db: Session = Depends(get_db)):
    return _detail(_quote(db, quote_id))


@router.post("/quotes/{quote_id}/bind", response_model=QuoteDetail, tags=["quotes"])
def bind_quote(quote_id: int, req: ActorRequest = ActorRequest(), db: Session = Depends(get_db)):
    """The customer accepts the quote."""
    return _detail(services.bind(db, _quote(db, quote_id), req.actor))


@router.post("/quotes/{quote_id}/issue", response_model=QuoteDetail, tags=["quotes"])
def issue_quote(quote_id: int, req: IssueRequest = IssueRequest(), db: Session = Depends(get_db)):
    """Turn a bound quote into a policy with a policy number and dates."""
    q = _quote(db, quote_id)
    services.issue(db, q, req.actor, req.start_date)
    return _detail(q)


@router.get("/quotes/{quote_id}/audit", response_model=list[AuditEventOut], tags=["audit"])
def quote_audit(quote_id: int, db: Session = Depends(get_db)):
    return _quote(db, quote_id).events


# ---------------------------------------------------------- underwriting

@router.get("/underwriting/queue", response_model=list[QuoteSummary], tags=["underwriting"])
def underwriting_queue(product: Optional[str] = None, db: Session = Depends(get_db)):
    """Referred quotes waiting for a human decision, oldest first."""
    stmt = select(Quote).where(Quote.status == "referred").order_by(Quote.id)
    if product:
        stmt = stmt.where(Quote.product == product)
    return [_summary(q) for q in db.scalars(stmt)]


@router.post("/quotes/{quote_id}/underwrite", response_model=QuoteDetail, tags=["underwriting"])
def underwrite_quote(quote_id: int, req: UnderwriteRequest, db: Session = Depends(get_db)):
    """Approve (optionally with a different premium) or decline a referred quote."""
    q = services.underwrite(db, _quote(db, quote_id), req.action, req.note, req.actor, req.override_premium)
    return _detail(q)


# ------------------------------------------------------- audit, policies

@router.get("/audit", response_model=list[AuditEventOut], tags=["audit"])
def recent_audit(limit: int = Query(100, ge=1, le=1000), db: Session = Depends(get_db)):
    return db.scalars(select(AuditEvent).order_by(AuditEvent.id.desc()).limit(limit)).all()


@router.get("/policies", response_model=list[PolicyOut], tags=["policies"])
def list_policies(product: Optional[str] = None, limit: int = Query(50, ge=1, le=500),
                  db: Session = Depends(get_db)):
    stmt = select(Policy).order_by(Policy.id.desc()).limit(limit)
    if product:
        stmt = stmt.where(Policy.product == product)
    return db.scalars(stmt).all()


@router.get("/policies/{policy_id}", response_model=PolicyOut, tags=["policies"])
def get_policy(policy_id: int, db: Session = Depends(get_db)):
    p = db.get(Policy, policy_id)
    if p is None:
        raise HTTPException(404, f"Policy {policy_id} not found")
    return p
