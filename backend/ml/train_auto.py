"""Train the Personal Auto claim-likelihood model.

Run from backend/:  python -m ml.train_auto
Reads   data/auto_applicants.csv
Writes  models/auto_risk.joblib  (pipeline + feature metadata + test metrics)

Target: had_claim_next_year (1 = the driver made a claim in the following year).
The model outputs a probability 0-1, used as the auto risk_score.
"""
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "auto_applicants.csv"
MODEL_PATH = ROOT / "models" / "auto_risk.joblib"
SEED = 42

# Features known at quote time. Deliberately excluded:
#   claim_amount_inr      -> only known after a claim (would leak the answer)
#   city                  -> city_tier carries the signal with far fewer categories
#   no_claim_bonus_pct    -> derived from prior claims + years licensed; it is a
#                            pricing discount in the rating engine, not a risk input
CATEGORICAL = ["vehicle_type", "parking"]
NUMERIC = ["driver_age", "years_licensed", "city_tier", "vehicle_age_years",
           "insured_declared_value_inr", "annual_km", "prior_claims_3y",
           "anti_theft_device"]
FEATURES = CATEGORICAL + NUMERIC

# Human-readable names for the UI's "top risk factors" panel.
LABELS = {
    "vehicle_type": "Vehicle type", "parking": "Overnight parking",
    "driver_age": "Driver age", "years_licensed": "Years licensed",
    "city_tier": "City tier", "vehicle_age_years": "Vehicle age",
    "insured_declared_value_inr": "Vehicle value (IDV)", "annual_km": "Annual km driven",
    "prior_claims_3y": "Claims in last 3 years", "anti_theft_device": "Anti-theft device",
}


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    """Select model features and make types consistent (bools -> 0/1)."""
    X = df[FEATURES].copy()
    X["anti_theft_device"] = X["anti_theft_device"].astype(int)
    return X


def build_pipeline() -> Pipeline:
    # Trees don't need one-hot encoding; ordinal codes keep one column per
    # feature, so each SHAP value maps straight back to one input field.
    pre = ColumnTransformer(
        [("cat", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1), CATEGORICAL)],
        remainder="passthrough",
        verbose_feature_names_out=False,
    )
    # Kept deliberately simple: claims are noisy, and deeper trees memorised the
    # training data (train AUC 0.84 vs test 0.62). Depth-2 trees with >=50
    # applicants per leaf were best in 5-fold cross-validation.
    gbm = GradientBoostingClassifier(
        n_estimators=150, learning_rate=0.05, max_depth=2, min_samples_leaf=50,
        subsample=0.8, random_state=SEED,
    )
    return Pipeline([("pre", pre), ("gbm", gbm)])


def decile_table(y_true, p) -> pd.DataFrame:
    """Actual claim rate per predicted-risk decile (10 = riskiest). A good model
    shows claim rates rising steadily from decile 1 to 10."""
    d = pd.DataFrame({"y": y_true, "p": p})
    d["decile"] = pd.qcut(d["p"].rank(method="first"), 10, labels=range(1, 11))
    return d.groupby("decile", observed=True).agg(
        avg_predicted=("p", "mean"), actual_claim_rate=("y", "mean"), n=("y", "size"))


def main():
    df = pd.read_csv(DATA)
    X, y = prepare(df), df["had_claim_next_year"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=SEED)

    # 5-fold cross-validated AUC on all data: steadier than one 1000-row test split.
    cv = StratifiedKFold(5, shuffle=True, random_state=SEED)
    cv_auc = cross_val_score(build_pipeline(), X, y, cv=cv, scoring="roc_auc")

    model = build_pipeline().fit(X_train, y_train)
    p_train = model.predict_proba(X_train)[:, 1]
    p_test = model.predict_proba(X_test)[:, 1]

    metrics = {
        "auc_train": round(roc_auc_score(y_train, p_train), 4),
        "auc_test": round(roc_auc_score(y_test, p_test), 4),
        "auc_cv_mean": round(float(cv_auc.mean()), 4),
        "auc_cv_std": round(float(cv_auc.std()), 4),
        "brier_test": round(brier_score_loss(y_test, p_test), 4),
        "claim_rate_test": round(float(y_test.mean()), 4),
        "avg_predicted_test": round(float(p_test.mean()), 4),
        "n_train": len(X_train), "n_test": len(X_test),
    }
    print("Metrics:", metrics)
    print("\nClaim rate by predicted-risk decile (test set):")
    print(decile_table(y_test.values, p_test).round(3).to_string())

    # Global importance: mean |SHAP| over the test set, per input feature.
    explainer = shap.TreeExplainer(model.named_steps["gbm"])
    sv = explainer.shap_values(model.named_steps["pre"].transform(X_test))
    names = list(model.named_steps["pre"].get_feature_names_out())
    importance = pd.Series(np.abs(sv).mean(axis=0), index=names).sort_values(ascending=False)
    print("\nGlobal feature importance (mean |SHAP|, log-odds):")
    print(importance.round(4).to_string())

    MODEL_PATH.parent.mkdir(exist_ok=True)
    joblib.dump({
        "pipeline": model,
        "features": FEATURES,
        "labels": LABELS,
        "metrics": metrics,
        "global_importance": importance.round(4).to_dict(),
        "sklearn_version": sklearn.__version__,
    }, MODEL_PATH)
    print(f"\nSaved {MODEL_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
