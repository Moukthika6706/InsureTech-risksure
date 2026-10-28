"""Impact preview: what would a proposed rule do to the sample book?

Before a rule is published, the underwriter sees how many sample applicants
it affects, how decisions change, how premiums move and what happens to the
loss ratio (the sample has real-looking claims, so we can measure it).

Rating and risk scoring don't depend on rules, so each product's sample book
is priced and scored once and cached; a preview then only re-runs the rules.

Run from backend/:  python -m engine.preview      # current rules on the sample
"""
from collections import Counter
from functools import lru_cache
from pathlib import Path

import pandas as pd

from engine.config import CONFIG_DIR, get_product, load_products, read_yaml
from engine.rating import rate, validate_applicant
from engine.risk import assess_many
from engine.rules import Rule, decide, load_rules, matches, parse_rule, rules_for

DATA_DIR = CONFIG_DIR.parent / "data"
DECISIONS = ["auto_approve", "approve_adjusted", "refer", "decline"]
EXAMPLES = 10


@lru_cache(maxsize=None)
def sample_book(code: str, config_dir: Path = CONFIG_DIR, data_dir: Path = DATA_DIR) -> list[dict]:
    """Every sample applicant priced and risk-scored once: [{id, facts, rated, claim}]."""
    settings = read_yaml(Path(config_dir) / "calibration.yaml")
    product = get_product(code, config_dir)
    df = pd.read_csv(Path(data_dir) / settings["data_file"].format(code=code))
    records = df.to_dict("records")
    data = [validate_applicant(product, r) for r in records]
    risks = assess_many(product, data, config_dir)
    return [{"id": r["applicant_id"], "claim": float(r[settings["claims_column"]]),
             "rated": rate(product, r)["premium"],
             "facts": {**d, "risk_score": s, "risk_band": b}}
            for r, d, (s, b) in zip(records, data, risks)]


def _outcome(product, row, rules) -> tuple[str, float]:
    decision, load = decide([r for r in rules if matches(r.when, row["facts"])])
    return decision, max(row["rated"] * (1 + load / 100), product.min_premium)


def book_summary(code: str, rules, config_dir: Path = CONFIG_DIR) -> dict:
    """Decision mix, premium and loss ratio of the sample book under a rule set."""
    product = get_product(code, config_dir)
    rules = rules_for(code, rules)
    out = [(row, *_outcome(product, row, rules)) for row in sample_book(code, config_dir)]
    written = [(row, prem) for row, d, prem in out if d != "decline"]   # referred counted as written
    premium = sum(p for _, p in written)
    return {"product": code, "applicants": len(out),
            "decisions": {d: n for d, n in Counter(d for _, d, _ in out).items()},
            "written_premium": round(premium, 2),
            "loss_ratio": round(sum(r["claim"] for r, _ in written) / premium, 4) if premium else None}


def preview_rule(raw_rule: dict, base_rules=None, config_dir: Path = CONFIG_DIR) -> dict:
    """Validate a proposed rule and report its impact on the sample book.

    A rule with the same id as an existing one is treated as a replacement.
    Raises RuleError if the rule is invalid.
    """
    products = load_products(Path(config_dir))
    rule: Rule = parse_rule(raw_rule, products)
    base = list(base_rules if base_rules is not None else load_rules(config_dir))
    replaces = any(r.id == rule.id for r in base)
    proposed = [r for r in base if r.id != rule.id] + [rule]
    codes = sorted(products) if rule.product == "*" else [rule.product]

    reports = []
    for code in codes:
        product = products[code]
        before_rules, after_rules = rules_for(code, base), rules_for(code, proposed)
        rows = []
        for row in sample_book(code, config_dir):
            d0, p0 = _outcome(product, row, before_rules)
            d1, p1 = _outcome(product, row, after_rules)
            rows.append((row, matches(rule.when, row["facts"]), d0, p0, d1, p1))

        def book(idx_d, idx_p):
            kept = [(r[0], r[idx_p]) for r in rows if r[idx_d] != "decline"]
            prem = sum(p for _, p in kept)
            return prem, (sum(x["claim"] for x, _ in kept) / prem if prem else None)

        prem0, lr0 = book(2, 3)
        prem1, lr1 = book(4, 5)
        hit = [r for r in rows if r[1]]
        priced = [r for r in hit if r[4] != "decline" and r[3] > 0]
        reports.append({
            "product": code,
            "applicants": len(rows),
            "matched": len(hit),
            "matched_pct": round(100 * len(hit) / len(rows), 2),
            "decisions_before": _counts(r[2] for r in rows),
            "decisions_after": _counts(r[4] for r in rows),
            "decisions_changed": sum(r[2] != r[4] for r in rows),
            "written_premium_before": round(prem0, 2),
            "written_premium_after": round(prem1, 2),
            "avg_premium_change_pct_matched": round(
                sum(100 * (r[5] / r[3] - 1) for r in priced) / len(priced), 2) if priced else 0.0,
            "loss_ratio_before": round(lr0, 4) if lr0 is not None else None,
            "loss_ratio_after": round(lr1, 4) if lr1 is not None else None,
            "examples": [{"applicant_id": r[0]["id"], "decision_before": r[2], "decision_after": r[4],
                          "premium_before": round(r[3], 2), "premium_after": round(r[5], 2)}
                         for r in hit[:EXAMPLES]],
        })
    return {"rule": rule.as_dict(), "replaces_existing": replaces, "products": reports}


def _counts(decisions) -> dict:
    c = Counter(decisions)
    return {d: c.get(d, 0) for d in DECISIONS}


def main():
    rules = load_rules()
    print(f"{len(rules)} rules loaded from config/rules.yaml\n")
    for code in sorted(load_products()):
        s = book_summary(code, rules)
        print(f"{code:9s} decisions {s['decisions']}  loss ratio of written book "
              f"{s['loss_ratio']:.1%}")


if __name__ == "__main__":
    main()
