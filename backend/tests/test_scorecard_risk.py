import pandas as pd
import pytest

from engine.config import CONFIG_DIR, get_product
from engine.rating import validate_applicant
from engine.risk import assess, assess_many
from engine.scorecard import band_for, load_scorecards, score

DATA = CONFIG_DIR.parent / "data"


@pytest.mark.parametrize("code", ["home", "business"])
def test_scorecard_matches_the_data_generator(code):
    # Single source of truth: the engine reads scorecards.yaml and reproduces
    # exactly the points and bands that generate_data.py wrote into the CSV.
    p = get_product(code)
    df = pd.read_csv(DATA / f"{code}_applicants.csv")
    for row in df.to_dict("records"):
        s = score(p, validate_applicant(p, row))
        assert (s["risk_score"], s["risk_band"]) == (row["scorecard_points"], row["risk_band"]), row["applicant_id"]


def test_scorecard_points_add_up():
    p = get_product("home")
    row = pd.read_csv(DATA / "home_applicants.csv").iloc[0].to_dict()
    s = score(p, validate_applicant(p, row))
    raw = s["base_points"] + sum(f["impact"] for f in s["factors"])
    assert s["risk_score"] == min(max(raw, 0), 100)


def test_security_features_reduce_points():
    p = get_product("home")
    row = validate_applicant(p, pd.read_csv(DATA / "home_applicants.csv").iloc[0].to_dict())
    none = {**row, "has_alarm": False, "has_cctv": False, "gated_community": False}
    all_ = {**row, "has_alarm": True, "has_cctv": True, "gated_community": True}
    card = load_scorecards()["home"]["factors"]["security"]
    assert score(p, none)["risk_score"] - score(p, all_)["risk_score"] == -sum(card.values())


def test_band_boundaries():
    bands = {"low": 25, "medium": 40, "high": 55}
    assert [band_for(s, bands) for s in (25, 26, 40, 55, 56)] == ["low", "medium", "medium", "high", "very_high"]


@pytest.mark.parametrize("code", ["auto", "home", "business"])
def test_single_and_batch_scoring_agree(code):
    p = get_product(code)
    rows = [validate_applicant(p, r) for r in
            pd.read_csv(DATA / f"{code}_applicants.csv").head(50).to_dict("records")]
    batch = assess_many(p, rows)
    for r, (s, b) in zip(rows, batch):
        one = assess(p, r)
        assert (one["risk_score"], one["risk_band"]) == (s, b)


def test_auto_risk_uses_configured_bands():
    p = get_product("auto")
    row = validate_applicant(p, pd.read_csv(DATA / "auto_applicants.csv").iloc[0].to_dict())
    out = assess(p, row)
    assert out["method"] == "ml_model" and out["unit"] == "claim probability"
    assert out["risk_band"] == band_for(out["risk_score"], p.risk["bands"])
    assert out["factors"] and all({"field", "label", "impact"} <= set(f) for f in out["factors"])
