"""Business operations used by the API routes. Pricing and decisions come from
engine/; this module only stores results and moves quotes through the lifecycle."""
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.lifecycle import transition
from app.models import Applicant, Policy, PublishedRule, Quote
from engine.config import get_product
from engine.quote import run_quote
from engine.rules import load_rules, parse_rule


class RequestError(ValueError):
    """A request that is well-formed but not allowed (HTTP 422)."""


def active_rules(db: Session) -> list:
    """rules.yaml + enabled published rules. A published rule with the same id
    as a YAML rule replaces it (that is how an underwriter edits a rule)."""
    published = [parse_rule(p.rule) for p in
                 db.scalars(select(PublishedRule).where(PublishedRule.enabled))]
    ids = {r.id for r in published}
    return [r for r in load_rules() if r.id not in ids] + published


def summary(q: Quote) -> dict:
    return {"risk_score": q.risk.get("risk_score"), "risk_band": q.risk.get("risk_band")}


def create_quote(db: Session, product: str, applicant: dict, coverages, actor: str,
                 source: str = "manual", external_ref: str = None) -> Quote:
    """Create a draft, rate it, and move it to quoted / referred / declined."""
    p = get_product(product)                                 # KeyError -> 404
    result = run_quote(product, applicant, coverages, rules=active_rules(db))   # ApplicantError -> 422

    app = Applicant(product=product, data=result["applicant"], source=source, external_ref=external_ref)
    quote = Quote(product=product, product_version=p.version, applicant=app, status="draft")
    db.add_all([app, quote])
    transition(db, quote, "create", actor, {"source": source})
    db.flush()                                               # assigns quote.id
    quote.quote_number = f"Q-{product[:3].upper()}-{quote.id:06d}"

    quote.decision = result["decision"]
    quote.coverages = result["coverages"]
    quote.base_premium = result["base_premium"]
    quote.rated_premium = result["rated_premium"]
    quote.premium = result["premium"]
    quote.total_load_pct = result["total_load_pct"]
    quote.breakdown = result["steps"]
    quote.risk = result["risk"]
    quote.rule_hits = result["rule_hits"]
    transition(db, quote, "rate", "system", {
        "decision": result["decision"], "premium": result["premium"],
        "risk_score": result["risk"]["risk_score"], "risk_band": result["risk"]["risk_band"],
        "rule_hits": [h["id"] for h in result["rule_hits"]]}, decision=result["decision"])
    db.commit()
    return quote


def underwrite(db: Session, quote: Quote, action: str, note: str, actor: str,
               override_premium: float = None) -> Quote:
    if override_premium is not None and action != "approve":
        raise RequestError("override_premium can only be set when approving")
    detail = {"note": note}
    if override_premium is not None:
        detail |= {"system_premium": quote.premium, "override_premium": override_premium}
    transition(db, quote, action, actor, detail)
    quote.underwriter_note = note
    if override_premium is not None:
        quote.override_premium = override_premium
    db.commit()
    return quote


def bind(db: Session, quote: Quote, actor: str) -> Quote:
    transition(db, quote, "bind", actor, {"premium": quote.final_premium})
    db.commit()
    return quote


def one_year_later(start: date) -> date:
    """Policy end date: the day before the anniversary (handles 29 February)."""
    try:
        return start.replace(year=start.year + 1) - timedelta(days=1)
    except ValueError:
        return date(start.year + 1, 2, 28)


def issue(db: Session, quote: Quote, actor: str, start_date: date = None) -> Policy:
    start = start_date or date.today()
    transition(db, quote, "issue", actor)                    # raises before anything is created
    policy = Policy(quote=quote, product=quote.product, premium=quote.final_premium,
                    start_date=start, end_date=one_year_later(start), policy_number="pending")
    db.add(policy)
    db.flush()
    policy.policy_number = f"P-{quote.product[:3].upper()}-{start.year}-{policy.id:06d}"
    quote.events[-1].detail = {"policy_number": policy.policy_number, "premium": policy.premium,
                               "start_date": start.isoformat(), "end_date": policy.end_date.isoformat()}
    db.commit()
    return policy


def dashboard(db: Session, product: str = None) -> dict:
    """Portfolio summary for the dashboard, optionally for one product."""
    q = select(Quote)
    if product:
        q = q.where(Quote.product == product)
    quotes = db.scalars(q).all()
    issued = [x for x in quotes if x.status == "issued"]

    def count(attr):
        out = {}
        for x in quotes:
            key = attr(x)
            if key is not None:
                out[key] = out.get(key, 0) + 1
        return out

    decided = [x for x in quotes if x.decision]
    straight_through = sum(x.decision in ("auto_approve", "approve_adjusted") for x in decided)
    pol = select(Policy.product, func.count(Policy.id), func.sum(Policy.premium)).group_by(Policy.product)
    if product:
        pol = pol.where(Policy.product == product)
    by_product = {p: {"quotes": 0, "policies": n, "written_premium": round(s or 0, 2)} for p, n, s in db.execute(pol)}
    for x in quotes:
        by_product.setdefault(x.product, {"quotes": 0, "policies": 0, "written_premium": 0.0})["quotes"] += 1

    return {
        "product": product,
        "quotes": len(quotes),
        "policies": len(issued),
        "written_premium": round(sum(p["written_premium"] for p in by_product.values()), 2),
        "average_premium": round(sum(x.final_premium for x in decided) / len(decided), 2) if decided else 0,
        "straight_through_rate": round(straight_through / len(decided), 4) if decided else None,
        "referral_rate": round(sum(x.decision == "refer" for x in decided) / len(decided), 4) if decided else None,
        "in_queue": sum(x.status == "referred" for x in quotes),
        "by_status": count(lambda x: x.status),
        "by_decision": count(lambda x: x.decision),
        "by_risk_band": count(lambda x: (x.risk or {}).get("risk_band")),
        "by_product": [{"product": p, **v} for p, v in sorted(by_product.items())],
    }
