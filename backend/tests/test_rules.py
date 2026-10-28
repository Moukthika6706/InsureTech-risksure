import pytest

from engine.config import get_product
from engine.preview import book_summary, preview_rule, sample_book
from engine.quote import run_quote
from engine.rules import RuleError, decide, load_rules, matches, parse_rule, underwrite

AUTO = dict(driver_age=35, years_licensed=12, city_tier=2, vehicle_type="hatchback",
            vehicle_age_years=3, insured_declared_value_inr=500_000, annual_km=10_000,
            prior_claims_3y=0, no_claim_bonus_pct=20, parking="garage", anti_theft_device=True)


def rule(**over):
    base = {"id": "test_rule", "product": "auto", "description": "A test rule",
            "when": {"all": [{"field": "driver_age", "op": "lt", "value": 25}]},
            "action": "refer", "reason": "Testing"}
    return {**base, **over}


def facts(**over):
    return {**AUTO, "risk_score": 0.05, "risk_band": "low", **over}


# ------------------------------------------------------------ validation

def test_rules_yaml_loads_and_validates():
    ids = [r.id for r in load_rules()]
    assert len(ids) == len(set(ids)) >= 10


def test_valid_rule_parses():
    assert parse_rule(rule()).action == "refer"


@pytest.mark.parametrize("bad, message", [
    (rule(when={"all": [{"field": "shoe_size", "op": "gt", "value": 9}]}), "unknown field"),
    (rule(when={"all": [{"field": "vehicle_type", "op": "lt", "value": "suv"}]}), "only works on numbers"),
    (rule(when={"all": [{"field": "vehicle_type", "op": "eq", "value": "tank"}]}), "must be one of"),
    (rule(when={"all": [{"field": "vehicle_type", "op": "in", "value": "suv"}]}), "non-empty list"),
    (rule(when={"all": [{"field": "driver_age", "op": "lt", "value": "young"}]}), "must be a number"),
    (rule(when={"all": [{"field": "risk_band", "op": "eq", "value": "scary"}]}), "must be one of"),
    (rule(when={"all": []}), "cannot be empty"),
    (rule(when={"all": [], "any": []}), "exactly one"),
    (rule(action="load"), "load_pct"),
    (rule(action="load", load_pct=500), "load_pct"),
    (rule(load_pct=10), "only allowed"),
    (rule(product="boat"), "unknown product"),
    (rule(id="Bad Id!"), "id"),
    ({**rule(), "priority": 1}, "Extra inputs"),
])
def test_invalid_rules_are_rejected(bad, message):
    with pytest.raises(RuleError, match=message):
        parse_rule(bad)


def test_wildcard_rule_needs_field_in_every_product():
    parse_rule(rule(product="*", when={"all": [{"field": "risk_band", "op": "eq", "value": "very_high"}]}))
    with pytest.raises(RuleError, match="home: unknown field 'driver_age'"):
        parse_rule(rule(product="*"))


# ------------------------------------------------------------ evaluation

@pytest.mark.parametrize("cond, expected", [
    ({"field": "driver_age", "op": "eq", "value": 35}, True),
    ({"field": "driver_age", "op": "ne", "value": 35}, False),
    ({"field": "driver_age", "op": "lt", "value": 35}, False),
    ({"field": "driver_age", "op": "lte", "value": 35}, True),
    ({"field": "driver_age", "op": "gt", "value": 30}, True),
    ({"field": "driver_age", "op": "gte", "value": 36}, False),
    ({"field": "vehicle_type", "op": "in", "value": ["suv", "hatchback"]}, True),
    ({"field": "vehicle_type", "op": "not_in", "value": ["suv", "hatchback"]}, False),
    ({"field": "city_tier", "op": "eq", "value": "2"}, True),          # 2 and "2" are the same
    ({"field": "anti_theft_device", "op": "eq", "value": True}, True),
    ({"field": "risk_band", "op": "gte", "value": "medium"}, False),  # bands are ordered
    ({"field": "risk_band", "op": "lt", "value": "high"}, True),
])
def test_operators(cond, expected):
    r = parse_rule(rule(when={"all": [cond]}))
    assert matches(r.when, facts()) is expected


def test_nested_any_inside_all():
    r = parse_rule(rule(when={"all": [
        {"field": "city_tier", "op": "eq", "value": 2},
        {"any": [{"field": "driver_age", "op": "lt", "value": 25},
                 {"field": "prior_claims_3y", "op": "gte", "value": 1}]}]}))
    assert not matches(r.when, facts())
    assert matches(r.when, facts(prior_claims_3y=2))


def _r(action, pct=0, id_="r"):
    return parse_rule(rule(id=f"{id_}_{action}", action=action, load_pct=pct))


def test_decision_precedence():
    assert decide([]) == ("auto_approve", 0.0)
    assert decide([_r("load", 10)]) == ("approve_adjusted", 10)
    assert decide([_r("load", 10), _r("refer")])[0] == "refer"
    assert decide([_r("load", 10), _r("refer"), _r("decline")])[0] == "decline"


def test_loads_add_up_and_show_in_breakdown():
    p = get_product("auto")
    rules = [_r("load", 20, "a"), _r("load", 30, "b")]
    out = underwrite(p, facts(driver_age=22), 10_000, rules)
    assert out["decision"] == "approve_adjusted"
    assert out["total_load_pct"] == 50
    assert out["premium"] == 15_000
    assert [s["amount_change"] for s in out["steps"]] == [2_000, 3_000]


def test_credit_cannot_go_below_minimum_premium():
    p = get_product("auto")
    out = underwrite(p, facts(driver_age=22), 3_000, [_r("load", -50)])
    assert out["premium"] == p.min_premium
    assert out["steps"][-1]["kind"] == "minimum"


def test_disabled_rule_is_ignored():
    r = parse_rule(rule(enabled=False))
    assert underwrite(get_product("auto"), facts(driver_age=20), 5_000, [r])["decision"] == "auto_approve"


# ---------------------------------------------------------- full quote

@pytest.mark.parametrize("code", ["auto", "home", "business"])
def test_run_quote_end_to_end(code):
    row = sample_book(code)[0]
    q = run_quote(code, row["facts"])
    assert q["decision"] in {"auto_approve", "approve_adjusted", "refer", "decline"}
    assert q["steps"][-1]["running_total"] == q["premium"]
    assert sum(s["amount_change"] for s in q["steps"]) == pytest.approx(q["premium"], abs=0.01)
    assert q["risk"]["risk_band"] in {"low", "medium", "high", "very_high"}


def test_quote_premium_includes_loads():
    load = [parse_rule(rule(id="always_load", action="load", load_pct=10,
                            when={"all": [{"field": "driver_age", "op": "gte", "value": 18}]}))]
    q = run_quote("auto", AUTO, rules=load)
    assert q["premium"] == pytest.approx(max(q["rated_premium"] * 1.10, 2500), abs=0.01)
    assert q["decision"] == "approve_adjusted"


# --------------------------------------------------------------- preview

def test_preview_counts_match_a_manual_count():
    r = rule(when={"all": [{"field": "driver_age", "op": "lt", "value": 21}]})
    out = preview_rule(r, base_rules=[])["products"][0]
    manual = sum(1 for row in sample_book("auto") if row["facts"]["driver_age"] < 21)
    assert out["matched"] == manual
    assert out["decisions_after"]["refer"] == manual
    assert out["decisions_changed"] == manual


def test_preview_of_rule_matching_nothing_changes_nothing():
    r = rule(when={"all": [{"field": "driver_age", "op": "gt", "value": 79},
                           {"field": "driver_age", "op": "lt", "value": 18}]})
    out = preview_rule(r)["products"][0]
    assert out["matched"] == 0 and out["decisions_changed"] == 0
    assert out["written_premium_before"] == out["written_premium_after"]


def test_preview_load_raises_premium_and_lowers_loss_ratio():
    r = rule(action="load", load_pct=40)
    out = preview_rule(r, base_rules=[])["products"][0]
    assert out["avg_premium_change_pct_matched"] == pytest.approx(40, abs=0.5)
    assert out["written_premium_after"] > out["written_premium_before"]
    assert out["loss_ratio_after"] < out["loss_ratio_before"]


def test_preview_decline_removes_business():
    out = preview_rule(rule(action="decline"), base_rules=[])["products"][0]
    assert out["decisions_after"]["decline"] == out["matched"] > 0
    assert out["written_premium_after"] < out["written_premium_before"]


def test_preview_replaces_rule_with_same_id():
    existing = load_rules()
    softer = existing[0].model_dump() | {"when": {"all": [{"field": "prior_claims_3y", "op": "gte", "value": 4}]}}
    out = preview_rule(softer)
    assert out["replaces_existing"] is True
    assert out["products"][0]["decisions_after"]["decline"] < out["products"][0]["decisions_before"]["decline"]


def test_preview_wildcard_covers_every_product():
    r = rule(product="*", when={"all": [{"field": "risk_band", "op": "eq", "value": "very_high"}]})
    assert {p["product"] for p in preview_rule(r)["products"]} == {"auto", "home", "business"}


def test_preview_rejects_invalid_rule():
    with pytest.raises(RuleError):
        preview_rule(rule(when={"all": [{"field": "nope", "op": "eq", "value": 1}]}))


def test_book_summary_counts_every_applicant():
    s = book_summary("home", load_rules())
    assert sum(s["decisions"].values()) == s["applicants"] == 2500
