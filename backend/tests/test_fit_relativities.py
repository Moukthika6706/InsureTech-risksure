import shutil

import numpy as np
import pandas as pd
import pytest

from engine import fit_relativities as fr
from engine.calibrate import calibrate
from engine.config import CONFIG_DIR, get_product, load_products, read_yaml
from engine.rating import lookup

DATA_DIR = CONFIG_DIR.parent / "data"
SETTINGS = read_yaml(CONFIG_DIR / "calibration.yaml")


def _sample(code):
    df = pd.read_csv(DATA_DIR / f"{code}_applicants.csv")
    return df, df["claim_amount_inr"].to_numpy(dtype=float)


@pytest.fixture(scope="module")
def applied(tmp_path_factory):
    """Fit + write + recalibrate home and business once, on a copy of config/."""
    d = tmp_path_factory.mktemp("config")
    for f in CONFIG_DIR.glob("*.yaml"):
        shutil.copy(f, d / f.name)
    result = fr.apply(d, products=["home", "business"], verbose=False)
    yield d, result
    load_products.cache_clear()


def test_fit_is_deterministic():
    p = get_product("home")
    df, claims = _sample("home")
    a = fr.fit_product(p, df, claims, SETTINGS["fitting"])
    b = fr.fit_product(p, df, claims, SETTINGS["fitting"])
    pd.testing.assert_frame_equal(a, b)


def test_portfolio_loss_ratio_is_65_after_recalibration(applied):
    config_dir, _ = applied
    check = calibrate(config_dir, products=["home", "business"], dry_run=True, verbose=False)
    for code, r in check.items():
        assert r["lr_before"] == pytest.approx(SETTINGS["target_loss_ratio"], abs=0.01), code


def test_second_write_changes_nothing(applied):
    config_dir, _ = applied
    text = {f.name: f.read_text(encoding="utf-8") for f in config_dir.glob("*.yaml")}
    again = fr.apply(config_dir, products=["home", "business"], verbose=False)
    assert not any(f["written"] for f in again["fits"].values())
    assert {f.name: f.read_text(encoding="utf-8") for f in config_dir.glob("*.yaml")} == text


def test_auto_is_left_untouched(applied):
    config_dir, _ = applied
    assert (config_dir / "auto.yaml").read_text(encoding="utf-8") == \
        (CONFIG_DIR / "auto.yaml").read_text(encoding="utf-8")


def test_written_yaml_keeps_prefit_values_and_one_header(applied):
    config_dir, _ = applied
    text = (config_dir / "business.yaml").read_text(encoding="utf-8")
    assert text.count("#[fit] FITTED on") == 1
    assert text.count("# pre-fit:") == len(get_product("business").rating_factors)


def test_levels_match_the_rating_engine():
    # The fit must group applicants exactly the way the rating engine prices them.
    for code in ("auto", "home", "business"):
        p = get_product(code)
        df, _ = _sample(code)
        for t in p.rating_factors:
            cur = fr.current_multipliers(t)
            for v in df[t.field].unique():
                assert cur[fr.level_index(t, v)] == lookup(t, v), (code, t.name, v)


def _rows(fitted, claims, factor="f"):
    n = len(fitted)
    return pd.DataFrame({"factor": factor, "level": [str(i) for i in range(n)], "level_no": range(n),
                         "current": 1.0, "fitted": fitted, "claims": claims,
                         "policies": [100 if c is not None else 0 for c in claims],
                         "reference": [i == 0 for i in range(n)], "col": None}).fillna({"claims": 0})


CFG = {"full_credibility_claims": 30, "cap": [0.5, 5.0], "monotonic_increasing": {"x": ["f"]}}


def test_low_credibility_level_is_blended_toward_one():
    out = fr.apply_safeguards(_rows([1.0, 4.0], [100, 30 / 4]), "y", CFG)   # Z = sqrt(7.5/30) = 0.5
    assert out["proposed"].iloc[1] == pytest.approx(2.0, abs=0.001)         # 4 ** 0.5
    assert "low credibility" in out["notes"].iloc[1]


def test_ordered_factor_never_decreases():
    out = fr.apply_safeguards(_rows([1.0, 2.0, 1.5, 3.0], [100, 100, 100, 100]), "x", CFG)
    p = out["proposed"].tolist()
    assert p == sorted(p)
    assert "order enforced" in out["notes"].iloc[2]


def test_multipliers_are_capped():
    out = fr.apply_safeguards(_rows([1.0, 20.0, 0.1], [100, 100, 100]), "y", CFG)
    assert out["proposed"].tolist() == [1.0, 5.0, 0.5]


def test_level_without_data_keeps_current():
    rows = _rows([1.0, np.nan], [100, None])
    rows.loc[1, "current"] = 1.6
    out = fr.apply_safeguards(rows, "y", CFG)
    assert out["proposed"].iloc[1] == 1.6
