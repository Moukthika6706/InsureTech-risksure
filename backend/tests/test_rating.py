import pandas as pd
import pytest

from engine.config import CONFIG_DIR, get_product, load_products
from engine.rating import ApplicantError, inr, rate

ROOT = CONFIG_DIR.parent

# A plain, low-risk auto applicant used across tests.
AUTO = dict(driver_age=35, years_licensed=12, city_tier=2, vehicle_type="hatchback",
            vehicle_age_years=3, insured_declared_value_inr=500_000, annual_km=10_000,
            prior_claims_3y=0, no_claim_bonus_pct=20, parking="garage",
            anti_theft_device=True)


def test_all_products_load_and_validate():
    assert set(load_products()) == {"auto", "home", "business"}


def test_auto_premium_matches_hand_calculation():
    # Coverages (defaults): third party 3,400 + own damage 2% x 5,00,000 + PA 750 = 14,150
    # Factors: vehicle age 3 -> x1.05, garage -> x0.95, everything else x1.00
    # Modifiers: NCB 20% -> x0.80, anti-theft -> x0.975
    expected = 14_150 * 1.05 * 0.95 * 0.80 * 0.975
    result = rate(get_product("auto"), AUTO)
    assert result["base_premium"] == 14_150
    assert result["premium"] == pytest.approx(expected, abs=0.01)


def test_breakdown_adds_up_exactly():
    result = rate(get_product("auto"), AUTO)
    steps = result["steps"]
    assert sum(s["amount_change"] for s in steps) == pytest.approx(result["premium"], abs=1e-9)
    assert steps[-1]["running_total"] == result["premium"]
    assert [s["step"] for s in steps] == list(range(1, len(steps) + 1))


def test_riskier_driver_pays_more():
    risky = {**AUTO, "driver_age": 20, "vehicle_type": "sports", "prior_claims_3y": 2,
             "no_claim_bonus_pct": 0, "parking": "street"}
    assert rate(get_product("auto"), risky)["premium"] > 2 * rate(get_product("auto"), AUTO)["premium"]


def test_band_upper_bound_is_inclusive():
    # driver_age band [20, 1.50]: age 20 is in it, age 21 falls into [24, 1.30]
    def age_mult(age):
        steps = rate(get_product("auto"), {**AUTO, "driver_age": age})["steps"]
        return next(s["multiplier"] for s in steps if s["code"] == "driver_age")
    assert age_mult(20) == 1.50
    assert age_mult(21) == 1.30


def test_optional_coverages():
    auto = get_product("auto")
    default = rate(auto, AUTO)
    with_addons = rate(auto, AUTO, coverages=["own_damage", "zero_depreciation", "roadside_assistance"])
    tp_only = rate(auto, AUTO, coverages=[])  # mandatory covers are always included
    codes = lambda r: [c["code"] for c in r["coverages"]]
    assert "zero_depreciation" not in codes(default)
    assert with_addons["premium"] > default["premium"]
    assert codes(tp_only) == ["third_party_liability", "personal_accident"]


def test_unknown_coverage_rejected():
    with pytest.raises(ApplicantError, match="unknown coverage"):
        rate(get_product("auto"), AUTO, coverages=["alien_abduction"])


def test_minimum_premium_applies():
    tiny = dict(business_type="it_office", city_tier=2, staff_count=2, annual_revenue_inr=500_000,
                handles_cash=False, prior_claims_5y=0, premises_sqft=200, building_age_years=2,
                flood_zone=1, fire_safety_certificate=True, sprinklers=True,
                property_sum_insured_inr=200_000, stock_value_inr=0, liability_limit_inr=2_500_000)
    result = rate(get_product("business"), tiny, coverages=[])
    assert result["premium"] == 2500
    assert result["steps"][-1]["kind"] == "minimum"


def test_validation_collects_all_errors():
    bad = {**AUTO, "driver_age": 15, "vehicle_type": "spaceship", "anti_theft_device": "maybe"}
    del bad["annual_km"]
    with pytest.raises(ApplicantError) as e:
        rate(get_product("auto"), bad)
    joined = " ".join(e.value.errors)
    for field in ("driver_age", "vehicle_type", "anti_theft_device", "annual_km"):
        assert field in joined


def test_string_inputs_are_coerced():
    # Values from HTML forms / CSV often arrive as strings.
    as_strings = {k: str(v) for k, v in AUTO.items()}
    assert rate(get_product("auto"), as_strings)["premium"] == rate(get_product("auto"), AUTO)["premium"]


@pytest.mark.parametrize("product", ["auto", "home", "business"])
def test_every_sample_applicant_rates(product):
    df = pd.read_csv(ROOT / "data" / f"{product}_applicants.csv")
    p = get_product(product)
    premiums = [rate(p, row)["premium"] for row in df.to_dict("records")]
    assert min(premiums) >= p.min_premium


def test_new_product_needs_only_a_yaml_file(tmp_path):
    # The core design promise: a brand-new product with zero engine changes.
    (tmp_path / "bicycle.yaml").write_text("""
kind: product
code: bicycle
name: Bicycle
version: "1.0"
risk: {method: none}
fields:
  - {name: bike_value, label: Bike value, type: int, min: 1000}
  - {name: locked_indoors, label: Kept indoors, type: bool}
coverages:
  - {code: theft, name: Theft, mandatory: true, basis: {type: percent_of, field: bike_value}, rate: 5}
modifiers:
  - {name: indoors, label: Indoors discount, field: locked_indoors, type: map, values: {true: 0.8, false: 1.0}}
""", encoding="utf-8")
    bike = get_product("bicycle", config_dir=tmp_path)
    assert rate(bike, {"bike_value": 20_000, "locked_indoors": True})["premium"] == 800


def test_config_typo_fails_loudly(tmp_path):
    (tmp_path / "broken.yaml").write_text("""
kind: product
code: broken
name: Broken
version: "1.0"
risk: {method: none}
fields:
  - {name: colour, label: Colour, type: select, options: [red, blue]}
coverages:
  - {code: c, name: C, mandatory: true, basis: {type: flat}, rate: 100}
rating_factors:
  - {name: colour, label: Colour, field: colour, type: map, values: {red: 1.0, bleu: 1.2}}
""", encoding="utf-8")
    with pytest.raises(ValueError, match="no multiplier for"):
        load_products(tmp_path)


def test_inr_formatting():
    assert inr(650000) == "₹6,50,000"
    assert inr(12345678) == "₹1,23,45,678"
    assert inr(999) == "₹999"
