"""Fill the database with a realistic demo book, using the REAL engines.

Each demo quote is a sample applicant from data/*.csv priced, scored and
decided by the same services the API uses. Then a month of activity is
played out: customers buy (bind) and get policies issued, underwriters
work the referral queue. Nothing is invented except who acted and when.

Run from backend/:  python -m app.seed            (adds to an empty database)
                    python -m app.seed --reset    (wipes everything first)
"""
import argparse
import random
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
from sqlalchemy import func, select

from app import services
from app.db import Base, SessionLocal, engine
from app.models import Applicant, AuditEvent, Policy, PublishedRule, Quote
from engine.config import CONFIG_DIR, load_products, read_yaml

SEED = 42
DEFAULT_COUNT = 400
MIX = {"auto": 0.45, "home": 0.30, "business": 0.25}   # share of demo quotes per product
DAYS = 30

# What customers and underwriters do with a decided quote (demo behaviour, not data).
BIND_RATE = 0.6          # quoted -> bought
ISSUE_RATE = 0.9         # bought -> policy issued
REFERRAL_OUTCOMES = [("approve", 0.35), ("approve_override", 0.12), ("decline", 0.13), ("pending", 0.40)]
UNDERWRITERS = ["Asha Menon", "Rahul Iyer", "Priya Shah"]
APPROVE_NOTES = ["Reviewed risk details; acceptable at the quoted premium.",
                 "Spoke to the broker; mitigations confirmed.",
                 "Within appetite after review of claims history."]
OVERRIDE_NOTES = ["Accept with a higher premium to reflect the risk.",
                  "Approved at a loaded premium pending risk survey."]
DECLINE_NOTES = ["Outside our risk appetite after review.",
                 "Risk too concentrated in this segment; declined."]


def sample_applicants(count: int, rng: random.Random) -> list[tuple[str, dict]]:
    settings = read_yaml(CONFIG_DIR / "calibration.yaml")
    # Split `count` by MIX so the parts add up exactly (largest remainder; plain
    # round() would turn 10 into 4 + 3 + 2 because it rounds halves to even).
    codes = list(load_products())
    exact = {c: count * MIX.get(c, 0) for c in codes}
    sizes = {c: int(exact[c]) for c in codes}
    for c in sorted(codes, key=lambda c: exact[c] - sizes[c], reverse=True)[:count - sum(sizes.values())]:
        sizes[c] += 1
    picked = []
    for code in codes:
        n = sizes[code]
        df = pd.read_csv(CONFIG_DIR.parent / "data" / settings["data_file"].format(code=code))
        rows = df.sample(n=n, random_state=rng.randint(0, 10**6)).to_dict("records")
        picked += [(code, r) for r in rows]
    rng.shuffle(picked)
    return picked


def _restamp(db, quote: Quote, start: datetime, rng: random.Random):
    """Give a quote's events realistic, increasing times starting at `start`."""
    t = start
    for e in db.scalars(select(AuditEvent).where(AuditEvent.quote_id == quote.id).order_by(AuditEvent.id)):
        e.created_at = t
        t += timedelta(minutes=rng.randint(1, 4) if e.action in ("create", "rate") else rng.randint(30, 60 * 48))
    quote.created_at, quote.updated_at = start, t
    if quote.policy:
        quote.policy.issued_at = t
    quote.applicant.created_at = start


def seed(count: int = DEFAULT_COUNT, reset: bool = False, verbose: bool = True) -> dict:
    Base.metadata.create_all(engine)
    rng = random.Random(SEED)
    db = SessionLocal()
    try:
        if reset:
            for table in (AuditEvent, Policy, Quote, Applicant, PublishedRule):   # children first
                db.query(table).delete()
            db.commit()
        if db.scalar(select(func.count(Quote.id))):
            raise SystemExit("Database already has quotes. Use --reset to replace them.")

        started = time.time()
        now = datetime.now(timezone.utc)
        for i, (code, row) in enumerate(sample_applicants(count, rng), start=1):
            q = services.create_quote(db, code, row, None, "customer", source="sample",
                                      external_ref=row["applicant_id"])
            created = now - timedelta(days=DAYS) + timedelta(seconds=rng.uniform(0, DAYS * 86400))
            if q.status == "referred":
                outcome = rng.choices([o for o, _ in REFERRAL_OUTCOMES], [w for _, w in REFERRAL_OUTCOMES])[0]
                who = rng.choice(UNDERWRITERS)
                if outcome == "approve":
                    services.underwrite(db, q, "approve", rng.choice(APPROVE_NOTES), who)
                elif outcome == "approve_override":
                    loaded = round(q.premium * rng.uniform(1.10, 1.30), -1)
                    services.underwrite(db, q, "approve", rng.choice(OVERRIDE_NOTES), who, loaded)
                elif outcome == "decline":
                    services.underwrite(db, q, "decline", rng.choice(DECLINE_NOTES), who)
            if q.status == "quoted" and rng.random() < BIND_RATE:
                services.bind(db, q, "customer")
                if rng.random() < ISSUE_RATE:
                    services.issue(db, q, "customer", start_date=(created + timedelta(days=rng.randint(1, 7))).date())
            _restamp(db, q, created, rng)
            db.commit()
            if verbose and i % 100 == 0:
                print(f"  {i} quotes...")

        summary = services.dashboard(db)
        if verbose:
            print(f"Seeded {summary['quotes']} quotes in {time.time() - started:.0f}s: "
                  f"{summary['policies']} policies, {summary['in_queue']} in the underwriting queue, "
                  f"straight-through {summary['straight_through_rate']:.0%}")
            print("  by status:", summary["by_status"])
        return summary
    finally:
        db.close()


def seed_if_empty():
    """Used on server start (SEED_DEMO_DATA=true): Render's free disk is wiped on
    every deploy, so an empty database gets the demo book again."""
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if db.scalar(select(func.count(Quote.id))):
            return None
    return seed(verbose=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--count", type=int, default=DEFAULT_COUNT)
    ap.add_argument("--reset", action="store_true", help="delete existing quotes, policies and published rules first")
    args = ap.parse_args()
    seed(args.count, args.reset)


if __name__ == "__main__":
    main()
