"""Risk scoring dispatcher: each product's `risk.method` says how it is scored.

  ml_model   claim probability (0-1) from a trained model, explained with SHAP
  scorecard  points (0-100) from config/scorecards.yaml, explained point by point

Both return the same shape, so the rules engine and the UI treat them alike:
  {method, risk_score, risk_band, unit, factors: [{field, label, value, impact, direction}]}
"""
from pathlib import Path

from engine import scorecard
from engine.config import CONFIG_DIR
from engine.schema import Product
from ml import auto_model


def assess(product: Product, data: dict, top_n: int = 5, config_dir: Path = CONFIG_DIR) -> dict:
    """Score one applicant (cleaned data from validate_applicant)."""
    method = product.risk["method"]
    if method == "ml_model":
        out = auto_model.score(data, top_n=top_n, model_file=product.risk["model"])
        factors = [{"field": f["feature"], "label": f["label"], "value": f["value"],
                    "impact": f["impact"], "direction": f["direction"]} for f in out["top_factors"]]
        return {"method": method, "risk_score": out["risk_score"],
                "risk_band": scorecard.band_for(out["risk_score"], product.risk["bands"]),
                "unit": "claim probability", "baseline": out["baseline_risk"], "factors": factors}
    if method == "scorecard":
        out = scorecard.score(product, data, config_dir)
        return {"method": method, "risk_score": out["risk_score"], "risk_band": out["risk_band"],
                "unit": "points", "baseline": out["base_points"], "factors": out["factors"][:top_n]}
    raise ValueError(f"Unknown risk method '{method}' for product {product.code}")


def assess_many(product: Product, rows: list[dict], config_dir: Path = CONFIG_DIR) -> list[tuple]:
    """(risk_score, risk_band) for many applicants, without explanations (fast)."""
    method = product.risk["method"]
    if method == "ml_model":
        probs = auto_model.score_many(rows, model_file=product.risk["model"])
        return [(p, scorecard.band_for(p, product.risk["bands"])) for p in probs]
    out = [scorecard.score(product, r, config_dir) for r in rows]
    return [(o["risk_score"], o["risk_band"]) for o in out]
