"""One quote, end to end: rate -> score risk -> underwrite.

This is what the API calls. The three engines stay separate and testable;
this module only wires them together into one explainable result.
"""
from pathlib import Path
from typing import Optional

from engine.config import CONFIG_DIR, get_product
from engine.rating import rate, validate_applicant
from engine.risk import assess
from engine.rules import load_rules, underwrite


def run_quote(product_code: str, applicant: dict, coverages: Optional[list[str]] = None,
              rules=None, config_dir: Path = CONFIG_DIR) -> dict:
    """Price, score and decide one applicant.

    `rules` defaults to config/rules.yaml; the API passes YAML + published rules.
    """
    product = get_product(product_code, config_dir)
    rating = rate(product, applicant, coverages)
    data = validate_applicant(product, applicant)
    risk = assess(product, data, config_dir=config_dir)
    facts = {**data, "risk_score": risk["risk_score"], "risk_band": risk["risk_band"]}
    uw = underwrite(product, facts, rating["premium"],
                    rules if rules is not None else load_rules(config_dir))

    steps = rating["steps"] + uw["steps"]
    for i, s in enumerate(steps, start=1):
        s["step"] = i
    return {
        "product": product.code,
        "currency": product.currency,
        "applicant": data,
        "coverages": rating["coverages"],
        "base_premium": rating["base_premium"],
        "rated_premium": rating["premium"],      # after rating factors and modifiers
        "premium": uw["premium"],                # after underwriting loads
        "steps": steps,
        "risk": risk,
        "decision": uw["decision"],
        "total_load_pct": uw["total_load_pct"],
        "rule_hits": uw["rule_hits"],
    }
