"""REST endpoints. Each handler is thin: validate input, call services/engine, shape output."""
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app import assistant, services
from app.db import get_db
from app.lifecycle import STATUSES
from app.models import AuditEvent, Policy, PublishedRule, Quote, now
from app.schemas import (ActorRequest, AuditEventOut, IssueRequest, PolicyOut, QuoteDetail,
                         QuoteRequest, QuoteSummary, RuleDraftRequest, RulePreviewRequest,
                         RulePublishRequest, UnderwriteRequest)
from engine.config import get_product, load_products
from engine.preview import preview_rule
from engine.quote import run_quote
from engine.rules import load_rules, parse_rule

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
             "risk_method": p.risk["method"], "currency": p.currency, "min_premium": p.min_premium,
             "coverages": [{"code": c.code, "name": c.name, "mandatory": c.mandatory} for c in p.coverages],
             "questions": len(p.fields)} for p in load_products().values()]


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
    stmt = select(Quote).order_by(Quote.created_at.desc(), Quote.id.desc()).limit(limit).offset(offset)
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
def recent_audit(limit: int = Query(100, ge=1, le=1000), product: Optional[str] = None,
                 db: Session = Depends(get_db)):
    """Most recent lifecycle events across all quotes (the dashboard's activity feed)."""
    stmt = select(AuditEvent).join(Quote).order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc()).limit(limit)
    if product:
        stmt = stmt.where(Quote.product == product)
    return [AuditEventOut.model_validate(e).model_copy(update={"quote_number": e.quote.quote_number,
                                                               "product": e.quote.product})
            for e in db.scalars(stmt)]


@router.get("/dashboard/summary", tags=["dashboard"])
def dashboard_summary(product: Optional[str] = None, db: Session = Depends(get_db)):
    """Portfolio KPIs: volumes, written premium, straight-through and referral rates, mixes."""
    if product:
        _product(product)
    return services.dashboard(db, product)


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


# ----------------------------------------------------------------- rules

@router.get("/rules", tags=["rules"])
def list_rules(db: Session = Depends(get_db)):
    """Active rules: config/rules.yaml plus rules published from the assistant."""
    published = {p.rule_id: p for p in db.scalars(select(PublishedRule))}
    out = [{**r.as_dict(), "source": "yaml"} for r in load_rules() if r.id not in published]
    out += [{**p.rule, "enabled": p.enabled, "source": "published", "published_by": p.published_by,
             "published_at": p.published_at, "source_text": p.source_text} for p in published.values()]
    return out


@router.get("/rules/examples", tags=["rules"])
def rule_examples():
    """Pre-written examples (also the assistant's fallback)."""
    return list(assistant.load_examples())


@router.post("/rules/draft", tags=["rules"])
def draft_rule(req: RuleDraftRequest, db: Session = Depends(get_db), client=Depends(assistant.get_client)):
    """English -> draft rule (AI, or the closest example if the AI is unavailable).
    Valid drafts come with an impact preview. Nothing is saved."""
    if req.product:
        _product(req.product)
    result = assistant.draft_rule(req.text, req.product, client=client)
    result["preview"] = preview_rule(result["rule"], base_rules=services.active_rules(db)) \
        if result["valid"] else None
    return result


@router.post("/rules/preview", tags=["rules"])
def preview(req: RulePreviewRequest, db: Session = Depends(get_db)):
    """Impact of a (possibly edited) rule on the sample book. Invalid rules -> 422."""
    return preview_rule(req.rule, base_rules=services.active_rules(db))


@router.post("/rules/publish", status_code=201, tags=["rules"])
def publish_rule(req: RulePublishRequest, db: Session = Depends(get_db)):
    """Save an approved rule. It is re-validated here: the browser is never trusted."""
    rule = parse_rule(req.rule)                                   # RuleError -> 422
    if not req.approved:
        raise services.RequestError("Publishing needs approved: true after reviewing the impact preview")
    existing = db.scalar(select(PublishedRule).where(PublishedRule.rule_id == rule.id))
    in_yaml = any(r.id == rule.id for r in load_rules())
    if (existing or in_yaml) and not req.replace:
        raise HTTPException(409, f"A rule with id '{rule.id}' already exists. Send replace: true to replace it.")
    impact = preview_rule(rule.as_dict(), base_rules=services.active_rules(db))
    row = existing or PublishedRule(rule_id=rule.id)
    row.product, row.rule, row.enabled = rule.product, rule.as_dict(), rule.enabled
    row.source_text, row.published_by, row.published_at = req.source_text, req.published_by, now()
    db.add(row)
    db.commit()
    return {"published": row.rule, "replaced": bool(existing or in_yaml), "preview": impact}


@router.post("/rules/{rule_id}/disable", tags=["rules"])
def disable_rule(rule_id: str, db: Session = Depends(get_db)):
    """Switch off a published rule (rules.yaml rules are changed in config instead)."""
    row = db.scalar(select(PublishedRule).where(PublishedRule.rule_id == rule_id))
    if row is None:
        raise HTTPException(404, f"No published rule '{rule_id}'")
    row.enabled = False
    row.rule = {**row.rule, "enabled": False}
    db.commit()
    return {"rule_id": rule_id, "enabled": False}
