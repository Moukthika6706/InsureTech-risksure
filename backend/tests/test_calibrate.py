import shutil

import pytest

from engine.calibrate import calibrate, fmt_rate, solve_multiplier
from engine.config import CONFIG_DIR, load_products, read_yaml

import numpy as np


@pytest.fixture
def config_copy(tmp_path):
    """A throwaway copy of config/ so tests never edit the real YAML files."""
    for f in CONFIG_DIR.glob("*.yaml"):
        shutil.copy(f, tmp_path / f.name)
    yield tmp_path
    load_products.cache_clear()


def _rates(config_dir):
    load_products.cache_clear()
    return {code: [c.rate for c in p.coverages] for code, p in load_products(config_dir).items()}


def test_calibrating_twice_gives_the_same_rates(config_copy):
    # Start from deliberately mis-priced rates so the first run has real work to do.
    first = calibrate(config_copy, target=0.5, verbose=False)
    assert all(r["written"] for r in first.values())
    rates_once = _rates(config_copy)
    text_once = {f.name: f.read_text(encoding="utf-8") for f in config_copy.glob("*.yaml")}

    second = calibrate(config_copy, target=0.5, verbose=False)
    assert not any(r["written"] for r in second.values())
    assert _rates(config_copy) == rates_once
    assert {f.name: f.read_text(encoding="utf-8") for f in config_copy.glob("*.yaml")} == text_once


def test_portfolio_loss_ratio_within_one_point_of_target(config_copy):
    target = read_yaml(config_copy / "calibration.yaml")["target_loss_ratio"]
    calibrate(config_copy, target=0.4, verbose=False)          # move rates away first
    calibrate(config_copy, verbose=False)                      # then calibrate to the setting
    check = calibrate(config_copy, dry_run=True, verbose=False)  # re-price with the real engine
    for code, r in check.items():
        assert abs(r["lr_before"] - target) <= 0.01, code


def test_rating_factors_are_not_changed(config_copy):
    before = {c: [f.model_dump() for f in p.rating_factors + p.modifiers]
              for c, p in load_products(config_copy).items()}
    calibrate(config_copy, target=0.5, verbose=False)
    load_products.cache_clear()
    after = {c: [f.model_dump() for f in p.rating_factors + p.modifiers]
             for c, p in load_products(config_copy).items()}
    assert before == after


def test_dry_run_writes_nothing(config_copy):
    text = {f.name: f.read_text(encoding="utf-8") for f in config_copy.glob("*.yaml")}
    calibrate(config_copy, target=0.3, dry_run=True, verbose=False)
    assert {f.name: f.read_text(encoding="utf-8") for f in config_copy.glob("*.yaml")} == text


def test_original_rate_is_kept_in_comment(config_copy):
    calibrate(config_copy, target=0.5, products=["auto"], verbose=False)
    calibrate(config_copy, target=0.8, products=["auto"], verbose=False)
    text = (config_copy / "auto.yaml").read_text(encoding="utf-8")
    assert "original 3400" in text          # the true original survives repeated runs
    # The 3-line header is replaced whole on every run, never stacked.
    assert text.count("CALIBRATED on") == 1
    assert text.count("coverage rates scaled") == 1
    assert text.count("#[calibration]") == 3


def test_solve_multiplier_respects_minimum_premium():
    raw = np.array([100.0, 1000.0])
    # Need 1,100 premium for 715 claims at 65%; min premium 500 lifts the small policy.
    k = solve_multiplier(raw, min_premium=500, total_claims=715, target=0.65)
    assert np.maximum(raw * k, 500).sum() == pytest.approx(1100)
    assert k == pytest.approx(0.6)


def test_fmt_rate_is_yaml_safe():
    assert fmt_rate(1000.4) == "1000"
    assert fmt_rate(0.588353) == "0.5884"
    assert fmt_rate(18151.2) == "18150"
    assert "e" not in fmt_rate(0.0000123456)
