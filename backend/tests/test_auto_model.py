import math

import pytest

from ml.auto_model import model_info, score

RISKY = dict(driver_age=20, years_licensed=1, city_tier=1, vehicle_type="sports",
             vehicle_age_years=2, insured_declared_value_inr=3_000_000, annual_km=25_000,
             prior_claims_3y=1, parking="street", anti_theft_device=False)
SAFE = dict(driver_age=45, years_licensed=25, city_tier=2, vehicle_type="hatchback",
            vehicle_age_years=3, insured_declared_value_inr=550_000, annual_km=7_000,
            prior_claims_3y=0, parking="garage", anti_theft_device=True)


def test_score_is_a_probability():
    s = score(SAFE)["risk_score"]
    assert 0 <= s <= 1


def test_risky_driver_scores_higher_than_safe_driver():
    assert score(RISKY)["risk_score"] > 3 * score(SAFE)["risk_score"]


def test_top_factors_sorted_and_labelled():
    factors = score(RISKY, top_n=3)["top_factors"]
    assert len(factors) == 3
    impacts = [abs(f["impact"]) for f in factors]
    assert impacts == sorted(impacts, reverse=True)
    assert all(f["label"] and f["direction"] for f in factors)


def test_shap_values_add_up_to_prediction():
    # SHAP's key property: baseline + all contributions = model output (log-odds).
    out = score(RISKY, top_n=100)
    logit = lambda p: math.log(p / (1 - p))
    total = logit(out["baseline_risk"]) + sum(f["impact"] for f in out["top_factors"])
    assert total == pytest.approx(logit(out["risk_score"]), abs=0.01)


def test_missing_field_raises():
    bad = {k: v for k, v in SAFE.items() if k != "driver_age"}
    with pytest.raises(ValueError, match="driver_age"):
        score(bad)


def test_saved_metrics_meet_minimum_quality():
    # Guards against accidentally saving a broken model.
    assert model_info()["metrics"]["auc_cv_mean"] > 0.90


def test_model_does_not_overfit():
    # Overfitting shows up as training AUC far above AUC on unseen data.
    m = model_info()["metrics"]
    assert m["auc_train"] - m["auc_cv_mean"] < 0.03
