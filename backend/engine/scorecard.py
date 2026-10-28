"""Points scorecard (home, business), read from config/scorecards.yaml.

A scorecard is a transparent risk score: start from base points, add or
subtract points per characteristic, clip to 0-100, then map to a band.
Every point is traceable, which is why insurers like scorecards where data
is thin. The engine understands four table shapes found in scorecards.yaml:

  map         {value: points}               e.g. roof_type: {asbestos: 14}
  bands       [[upper_bound, points], ...]  e.g. building_age_years
  count       {per_claim, max_claims_counted}
  flag group  {sub_factor: points} where each sub-factor is a yes/no field,
              named in the product's risk.field_map as "factor.sub_factor"
"""
from functools import lru_cache
from pathlib import Path

from engine.config import CONFIG_DIR, read_yaml
from engine.schema import Product, norm_key

TOP_BAND = "very_high"   # scorecards.yaml convention: above the last upper bound


@lru_cache(maxsize=None)
def load_scorecards(config_dir: Path = CONFIG_DIR) -> dict:
    return read_yaml(Path(config_dir) / "scorecards.yaml")


def band_for(score: float, bands: dict) -> str:
    """bands = {label: upper_bound, ...} in ascending order."""
    for label, upper in bands.items():
        if score <= upper:
            return label
    return TOP_BAND


def _band_points(value, bands):
    for upper, pts in bands:
        if value <= upper:
            return pts
    return bands[-1][1]


def score(product: Product, data: dict, config_dir: Path = CONFIG_DIR) -> dict:
    """Score cleaned applicant data. Returns points, band and every contribution."""
    card = load_scorecards(Path(config_dir))[product.risk["scorecard"]]
    fmap = product.risk.get("field_map", {})
    label = lambda field: product.field(field).label if any(f.name == field for f in product.fields) else field
    parts = []

    for name, table in card["factors"].items():
        field = fmap.get(name, name)
        if isinstance(table, list):                                   # bands
            parts.append((field, _band_points(data[field], table)))
        elif set(table) == {"per_claim", "max_claims_counted"}:      # count
            n = min(int(data[field]), table["max_claims_counted"])
            parts.append((field, table["per_claim"] * n))
        elif any(f"{name}.{sub}" in fmap for sub in table):          # flag group
            for sub, pts in table.items():
                sub_field = fmap[f"{name}.{sub}"]
                parts.append((sub_field, pts if data[sub_field] else 0))
        else:                                                         # map
            pts = next((p for k, p in table.items() if norm_key(k) == norm_key(data[field])), None)
            if pts is None:
                raise ValueError(f"scorecard '{name}' has no points for {data[field]!r}")
            parts.append((field, pts))

    raw = card["base"] + sum(p for _, p in parts)
    points = int(min(max(raw, card["min"]), card["max"]))
    factors = [{"field": f, "label": label(f), "value": data[f], "impact": p,
                "direction": "increases risk" if p > 0 else "decreases risk"}
               for f, p in parts if p != 0]
    factors.sort(key=lambda x: abs(x["impact"]), reverse=True)
    return {"risk_score": points, "risk_band": band_for(points, card["bands"]),
            "base_points": card["base"], "factors": factors}
