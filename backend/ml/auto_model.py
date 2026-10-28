"""Score one auto applicant: claim probability + top SHAP factors.

Used by the API (quote creation, what-if simulator). The model is loaded once
and cached; train it first with `python -m ml.train_auto`.
"""
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap

MODELS_DIR = Path(__file__).resolve().parents[2] / "models"
MODEL_PATH = MODELS_DIR / "auto_risk.joblib"
DEFAULT_MODEL = MODEL_PATH.name


@lru_cache(maxsize=None)
def _load(model_file: str = DEFAULT_MODEL):
    bundle = joblib.load(MODELS_DIR / model_file)
    pipe = bundle["pipeline"]
    explainer = shap.TreeExplainer(pipe.named_steps["gbm"])
    return bundle, pipe, explainer


def _frame(rows: list[dict], features: list[str]) -> pd.DataFrame:
    missing = [f for f in features if f not in rows[0]]
    if missing:
        raise ValueError(f"Missing auto fields: {missing}")
    X = pd.DataFrame([{f: r[f] for f in features} for r in rows])
    X["anti_theft_device"] = X["anti_theft_device"].astype(int)
    return X


def model_info(model_file: str = DEFAULT_MODEL) -> dict:
    """Metrics and global importance saved at training time (for the UI/README)."""
    bundle, _, _ = _load(model_file)
    return {"metrics": bundle["metrics"], "global_importance": bundle["global_importance"]}


def score_many(rows: list[dict], model_file: str = DEFAULT_MODEL) -> list[float]:
    """Claim probabilities for many applicants at once (no SHAP; used by the rule preview)."""
    bundle, pipe, _ = _load(model_file)
    return [round(float(p), 4) for p in pipe.predict_proba(_frame(rows, bundle["features"]))[:, 1]]


def score(applicant: dict, top_n: int = 5, model_file: str = DEFAULT_MODEL) -> dict:
    """Return {risk_score, baseline_risk, top_factors} for one applicant.

    SHAP splits the prediction into per-feature contributions (in log-odds):
    positive = pushes claim risk up, negative = pushes it down. Added to the
    baseline (the average applicant), they give exactly the model's output.
    """
    bundle, pipe, explainer = _load(model_file)
    X = _frame([applicant], bundle["features"])

    prob = float(pipe.predict_proba(X)[0, 1])
    contrib = explainer.shap_values(pipe.named_steps["pre"].transform(X))[0]
    names = pipe.named_steps["pre"].get_feature_names_out()

    factors = [
        {
            "feature": name,
            "label": bundle["labels"].get(name, name),
            "value": applicant[name],
            "impact": round(float(c), 4),
            "direction": "increases risk" if c > 0 else "decreases risk",
        }
        for name, c in zip(names, contrib)
    ]
    factors.sort(key=lambda f: abs(f["impact"]), reverse=True)

    # expected_value is a 1-element array (log-odds); convert to a probability.
    base_logit = float(np.ravel(explainer.expected_value)[0])
    return {
        "risk_score": round(prob, 4),
        "baseline_risk": round(1 / (1 + np.exp(-base_logit)), 4),
        "top_factors": factors[:top_n],
    }
