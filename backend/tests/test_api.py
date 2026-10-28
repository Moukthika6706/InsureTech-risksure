from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.lifecycle import InvalidTransition, transition
from app.main import app
from app.models import PublishedRule, Quote
from app.services import one_year_later

SAFE = dict(driver_age=35, years_licensed=12, city_tier=2, vehicle_type="hatchback",
            vehicle_age_years=3, insured_declared_value_inr=500_000, annual_km=10_000,
            prior_claims_3y=0, no_claim_bonus_pct=20, parking="garage", anti_theft_device=True)
YOUNG_SPORTS = {**SAFE, "driver_age": 20, "years_licensed": 1, "vehicle_type": "sports",
                "insured_declared_value_inr": 3_000_000, "no_claim_bonus_pct": 0,
                "parking": "street", "anti_theft_device": False}
MANY_CLAIMS = {**SAFE, "prior_claims_3y": 3, "no_claim_bonus_pct": 0}


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


def new_quote(client, applicant=SAFE, product="auto", **extra):
    r = client.post("/quotes", json={"product": product, "applicant": applicant, **extra})
    assert r.status_code == 201, r.text
    return r.json()


def actions(client, qid):
    return [(e["action"], e["from_status"], e["to_status"]) for e in client.get(f"/quotes/{qid}/audit").json()]


# --------------------------------------------------------------- products

def test_products_list_and_detail(client):
    assert {p["code"] for p in client.get("/products").json()} == {"auto", "home", "business"}
    auto = client.get("/products/auto").json()
    assert {f["name"] for f in auto["fields"]} >= {"driver_age", "vehicle_type"}
    assert client.get("/products/boat").status_code == 404


def test_rate_saves_nothing(client):
    r = client.post("/rate", json={"product": "auto", "applicant": SAFE})
    assert r.status_code == 200
    assert r.json()["decision"] == "auto_approve" and r.json()["premium"] > 0
    assert client.get("/quotes").json() == []


# ------------------------------------------------------------- lifecycle

def test_happy_path_quote_bind_issue(client):
    q = new_quote(client)
    assert q["status"] == "quoted" and q["quote_number"] == "Q-AUT-000001"
    assert q["breakdown"][-1]["running_total"] == q["premium"]
    assert client.post(f"/quotes/{q['id']}/bind", json={"actor": "asha"}).json()["status"] == "bound"
    issued = client.post(f"/quotes/{q['id']}/issue", json={"start_date": "2026-11-01"}).json()
    assert issued["status"] == "issued"
    pol = issued["policy"]
    assert pol["policy_number"] == "P-AUT-2026-000001"
    assert (pol["start_date"], pol["end_date"]) == ("2026-11-01", "2027-10-31")
    assert pol["premium"] == q["premium"]
    assert actions(client, q["id"]) == [("create", None, "draft"), ("rate", "draft", "quoted"),
                                        ("bind", "quoted", "bound"), ("issue", "bound", "issued")]
    assert client.get("/policies").json()[0]["policy_number"] == pol["policy_number"]


@pytest.mark.parametrize("applicant, status, decision", [
    (SAFE, "quoted", "auto_approve"),
    (YOUNG_SPORTS, "referred", "refer"),
    (MANY_CLAIMS, "declined", "decline"),
])
def test_rating_decides_the_first_status(client, applicant, status, decision):
    q = new_quote(client, applicant)
    assert (q["status"], q["decision"]) == (status, decision)
    assert actions(client, q["id"])[-1] == ("rate", "draft", status)


@pytest.mark.parametrize("applicant, action", [
    (YOUNG_SPORTS, "bind"),      # referred: an underwriter must approve first
    (MANY_CLAIMS, "bind"),       # declined
    (SAFE, "issue"),             # quoted but not bound yet
])
def test_invalid_transitions_return_409(client, applicant, action):
    q = new_quote(client, applicant)
    r = client.post(f"/quotes/{q['id']}/{action}")
    assert r.status_code == 409
    assert f"Cannot {action}" in r.json()["detail"]
    assert len(actions(client, q["id"])) == 2     # nothing was recorded


def test_cannot_bind_twice(client):
    q = new_quote(client)
    client.post(f"/quotes/{q['id']}/bind")
    assert client.post(f"/quotes/{q['id']}/bind").status_code == 409


# ---------------------------------------------------------- underwriting

def test_referred_quote_is_in_queue_and_can_be_approved_with_override(client):
    q = new_quote(client, YOUNG_SPORTS)
    queue = client.get("/underwriting/queue").json()
    assert [x["id"] for x in queue] == [q["id"]] and queue[0]["rule_hits"]

    r = client.post(f"/quotes/{q['id']}/underwrite",
                    json={"action": "approve", "note": "Parent is main driver", "override_premium": 250000})
    body = r.json()
    assert body["status"] == "quoted" and body["final_premium"] == 250000
    assert body["premium"] == q["premium"]                    # the system price is kept for the record
    assert client.get("/underwriting/queue").json() == []
    event = client.get(f"/quotes/{q['id']}/audit").json()[-1]
    assert event["action"] == "approve" and event["actor"] == "underwriter"
    assert event["detail"] == {"note": "Parent is main driver", "system_premium": q["premium"],
                               "override_premium": 250000}

    client.post(f"/quotes/{q['id']}/bind")
    issued = client.post(f"/quotes/{q['id']}/issue").json()
    assert issued["policy"]["premium"] == 250000               # the policy uses the override


def test_underwriter_decline(client):
    q = new_quote(client, YOUNG_SPORTS)
    r = client.post(f"/quotes/{q['id']}/underwrite", json={"action": "decline", "note": "Outside appetite"})
    assert r.json()["status"] == "declined"
    assert client.post(f"/quotes/{q['id']}/bind").status_code == 409


def test_underwrite_rules(client):
    referred = new_quote(client, YOUNG_SPORTS)
    quoted = new_quote(client)
    url = f"/quotes/{referred['id']}/underwrite"
    assert client.post(url, json={"action": "approve"}).status_code == 422                 # note required
    assert client.post(url, json={"action": "decline", "note": "no", "override_premium": 1}).status_code == 422
    assert client.post(url, json={"action": "decline", "note": "nope", "override_premium": 1}).status_code == 422
    assert client.post(f"/quotes/{quoted['id']}/underwrite",
                       json={"action": "approve", "note": "fine"}).status_code == 409    # not referred


# ------------------------------------------------------- errors, listing

def test_invalid_applicant_returns_all_errors(client):
    bad = {**SAFE, "driver_age": 15, "vehicle_type": "tank"}
    r = client.post("/quotes", json={"product": "auto", "applicant": bad})
    assert r.status_code == 422
    assert len(r.json()["errors"]) == 2
    assert client.post("/quotes", json={"product": "boat", "applicant": {}}).status_code == 404
    assert client.get("/quotes/999").status_code == 404


def test_list_filters(client):
    new_quote(client)
    new_quote(client, YOUNG_SPORTS)
    home = {"city_tier": 1, "area_sqft": 1000, "home_value_inr": 10_000_000, "building_age_years": 10,
            "construction": "rcc_frame", "roof_type": "rcc_slab", "occupancy": "owner_occupied",
            "flood_zone": 1, "fire_station_km": 1.5, "gated_community": True, "has_alarm": True,
            "has_cctv": True, "prior_claims_5y": 0, "building_sum_insured_inr": 8_000_000,
            "contents_sum_insured_inr": 1_000_000}
    h = new_quote(client, home, product="home")
    assert h["quote_number"].startswith("Q-HOM-")
    assert len(client.get("/quotes").json()) == 3
    assert [q["product"] for q in client.get("/quotes?product=home").json()] == ["home"]
    assert len(client.get("/quotes?status=referred").json()) == 1
    assert client.get("/quotes?status=nonsense").status_code == 422
    assert len(client.get("/audit").json()) == 6


def test_published_rule_changes_decisions(client, db_session):
    """Rules stored in the DB (Step 7) are merged with rules.yaml when quoting."""
    assert new_quote(client)["status"] == "quoted"
    with db_session() as db:
        db.add(PublishedRule(rule_id="refer_tier2", product="auto", published_by="test", rule={
            "id": "refer_tier2", "product": "auto", "description": "Refer tier 2 cities",
            "when": {"all": [{"field": "city_tier", "op": "eq", "value": 2}]},
            "action": "refer", "reason": "Testing published rules"}))
        db.commit()
    q = new_quote(client)
    assert q["status"] == "referred"
    assert "refer_tier2" in [h["id"] for h in q["rule_hits"]]


# ------------------------------------------------------------ unit tests

def test_transition_table_directly(db_session):
    with db_session() as db:
        q = Quote(product="auto", product_version="1.0", applicant_id=1, status="draft")
        transition(db, q, "create", "t")
        db.add(q)
        db.flush()
        with pytest.raises(InvalidTransition):
            transition(db, q, "issue", "t")
        transition(db, q, "rate", "t", decision="approve_adjusted")
        assert q.status == "quoted"


def test_policy_end_date_handles_leap_day():
    assert one_year_later(date(2026, 1, 15)) == date(2027, 1, 14)
    assert one_year_later(date(2028, 2, 29)) == date(2029, 2, 28)
