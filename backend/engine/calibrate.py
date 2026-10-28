"""Calibrate each product's base rates so the sample portfolio hits a target loss ratio.

Loss ratio = total claims / total premium. We price every sample applicant
with the real rating engine, then find ONE multiplier k for the product's
coverage rates so that  claims / premium(k) = target. Rating factors are not
touched, so the relativities between applicants stay exactly as configured.

Run from backend/:
    python -m engine.calibrate --dry-run      # report only
    python -m engine.calibrate                # report and write rates to YAML
    python -m engine.calibrate --target 0.6 --product home
"""
import argparse
import math
import re
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from engine.config import CONFIG_DIR, load_products, read_yaml
from engine.rating import inr, rate
from engine.schema import Product

DATA_DIR = CONFIG_DIR.parent / "data"
RATE_TOLERANCE = 0.0005   # |k - 1| below this counts as "already calibrated"


# ----------------------------------------------------------------- maths

def price_portfolio(product: Product, df: pd.DataFrame) -> np.ndarray:
    """Premium per applicant BEFORE the minimum-premium floor.

    The pre-floor premium is linear in the coverage rates, so scaling every
    rate by k scales it by exactly k. The floor is re-applied separately.
    """
    raw = []
    for row in df.to_dict("records"):
        steps = rate(product, row)["steps"]
        pre_floor = [s for s in steps if s["kind"] != "minimum"]
        raw.append(pre_floor[-1]["running_total"])
    return np.array(raw)


def floored(raw: np.ndarray, k: float, min_premium: float) -> np.ndarray:
    return np.maximum(raw * k, min_premium)


def solve_multiplier(raw, min_premium, total_claims, target) -> float:
    """Find k so that sum(max(k * raw, min_premium)) = total_claims / target.

    Total premium rises steadily with k, so a simple bisection finds it.
    """
    needed = total_claims / target
    if floored(raw, 0, min_premium).sum() > needed:
        raise ValueError("Minimum premiums alone exceed the premium needed for this target.")
    lo, hi = 0.0, 1.0
    while floored(raw, hi, min_premium).sum() < needed:
        hi *= 2
    for _ in range(100):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if floored(raw, mid, min_premium).sum() < needed else (lo, mid)
    return (lo + hi) / 2


# ---------------------------------------------------------------- report

def segment_labels(df: pd.DataFrame, seg: dict) -> pd.Series:
    col = df[seg["column"]]
    if "bands" not in seg:
        return col.astype(str)
    def band(v):
        for upper, label in seg["bands"]:
            if v <= upper:
                return label
        return seg["bands"][-1][1]
    return col.apply(band)


def segment_table(df, claims, before, after, seg, target, flag_points) -> pd.DataFrame:
    d = pd.DataFrame({"segment": segment_labels(df, seg), "claims": claims,
                      "before": before, "after": after})
    t = d.groupby("segment", sort=False).agg(
        policies=("claims", "size"), claims=("claims", "sum"),
        premium_before=("before", "sum"), premium_after=("after", "sum"))
    order = [b[1] for b in seg["bands"]] if "bands" in seg else seg.get("order")
    t = t.reindex([o for o in order if o in t.index]) if order else t.sort_index()
    t["lr_before"] = t["claims"] / t["premium_before"]
    t["lr_after"] = t["claims"] / t["premium_after"]
    t["flag"] = np.where((t["lr_after"] - target).abs() * 100 > flag_points,
                         f">{flag_points} pts off", "")
    return t


def pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def print_report(r: dict, target: float):
    print(f"\n=== {r['name']} ({r['code']}) — {r['policies']:,} sample policies ===")
    print(f"Total claims        {inr(r['claims'])}")
    print(f"Total premium       {inr(r['premium_before'])}  ->  {inr(r['premium_after'])}")
    print(f"Loss ratio          {pct(r['lr_before'])}  ->  {pct(r['lr_after'])}   (target {pct(target)})")
    print(f"Rate multiplier     x{r['multiplier']:.4f}")
    print(f"Average premium     {inr(r['avg_before'])}  ->  {inr(r['avg_after'])}")
    print(f"Premium / insured value  {r['pct_value_before']:.3f}%  ->  {r['pct_value_after']:.3f}%")
    print(f"At minimum premium  {r['floored_before']}  ->  {r['floored_after']} policies")
    for name, t in r["segments"].items():
        show = t.copy()
        for c in ("lr_before", "lr_after"):
            show[c] = show[c].map(pct)
        for c in ("claims", "premium_before", "premium_after"):
            show[c] = show[c].map(inr)
        print(f"\n  Loss ratio by {name}:")
        print("  " + show.to_string().replace("\n", "\n  "))


# ----------------------------------------------------------- YAML update

def fmt_rate(x: float, sig: int = 4) -> str:
    """Round to 4 significant figures without scientific notation (YAML-safe)."""
    decimals = sig - int(math.floor(math.log10(abs(x)))) - 1   # negative for big numbers
    value = round(x, decimals)
    if decimals <= 0:
        return str(int(value))
    return f"{value:.{decimals}f}".rstrip("0").rstrip(".")


RATE_LINE = re.compile(r"^(\s+rate:\s*)([0-9.]+)(\s*#.*)?$")
ORIGINAL = re.compile(r"original ([0-9.]+)")


def write_rates(path: Path, k: float, target: float, today: str) -> dict:
    """Scale every `rate:` under `coverages:` by k, editing the text so comments survive.

    Each rate line keeps its pre-calibration value in a comment, and a header
    above `coverages:` records the target, overall multiplier and date.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    out, in_coverages, current, new_rates, ratio = [], False, None, {}, None
    for line in lines:
        if line and not line[0].isspace() and not line.startswith(("#", "-")):
            in_coverages = line.startswith("coverages:")
        code = re.match(r"^\s*- code:\s*(\S+)", line)
        if in_coverages and code:
            current = code.group(1)
        m = RATE_LINE.match(line)
        if in_coverages and current and m:
            old = float(m.group(2))
            prior = ORIGINAL.search(m.group(3) or "")
            original = float(prior.group(1)) if prior else old
            new = fmt_rate(old * k)
            new_rates[current] = float(new)
            ratio = ratio or float(new) / original
            line = f"{m.group(1)}{new}  # calibrated; original {original:g}"
            current = None
        out.append(line)

    # Replace any previous calibration header with a fresh one.
    out = [l for l in out if not l.startswith("# CALIBRATED")]
    i = next(n for n, l in enumerate(out) if l.startswith("coverages:"))
    out[i:i] = [
        f"# CALIBRATED on the synthetic sample (data/{path.stem}_applicants.csv) on {today}:",
        f"# coverage rates scaled x{ratio:.4f} vs original to target loss ratio {target:g}.",
        "# Illustrative only — not real actuarial pricing.",
    ]
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return new_rates


# ------------------------------------------------------------------ main

def calibrate(config_dir: Path = CONFIG_DIR, data_dir: Path = DATA_DIR, target: float = None,
              products: list[str] = None, dry_run: bool = False, verbose: bool = True) -> dict:
    """Calibrate products and return a result dict per product code (importable)."""
    settings = read_yaml(Path(config_dir) / "calibration.yaml")
    target = target if target is not None else settings["target_loss_ratio"]
    all_products = load_products(Path(config_dir))
    results = {}

    for code in products or sorted(all_products):
        product = all_products[code]
        df = pd.read_csv(Path(data_dir) / settings["data_file"].format(code=code))
        claims = df[settings["claims_column"]].to_numpy(dtype=float)
        raw = price_portfolio(product, df)
        minp = product.min_premium
        k = solve_multiplier(raw, minp, claims.sum(), target)
        before, after = floored(raw, 1.0, minp), floored(raw, k, minp)
        value = df[settings["insured_value"][code]].sum(axis=1).to_numpy(dtype=float)

        r = {
            "code": code, "name": product.name, "policies": len(df),
            "claims": claims.sum(), "multiplier": k,
            "premium_before": before.sum(), "premium_after": after.sum(),
            "lr_before": claims.sum() / before.sum(), "lr_after": claims.sum() / after.sum(),
            "avg_before": before.mean(), "avg_after": after.mean(),
            "pct_value_before": before.sum() / value.sum() * 100,
            "pct_value_after": after.sum() / value.sum() * 100,
            "floored_before": int((raw < minp).sum()), "floored_after": int((raw * k < minp).sum()),
            "segments": {s["name"]: segment_table(df, claims, before, after, s, target,
                                                  settings["flag_points"])
                         for s in settings["segments"].get(code, [])},
            "written": False,
        }
        if verbose:
            print_report(r, target)

        if not dry_run and abs(k - 1) > RATE_TOLERANCE:
            r["new_rates"] = write_rates(Path(config_dir) / f"{code}.yaml", k, target,
                                         date.today().isoformat())
            r["written"] = True
        if verbose:
            print("\n  -> " + ("rates written to " + f"config/{code}.yaml" if r["written"] else
                             "dry run, nothing written" if dry_run else "already calibrated, unchanged"))
        results[code] = r

    load_products.cache_clear()   # later callers must see the new rates
    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="print the report, don't edit YAML")
    ap.add_argument("--target", type=float, help="override target_loss_ratio from calibration.yaml")
    ap.add_argument("--product", action="append", help="only this product (repeatable)")
    args = ap.parse_args()
    calibrate(target=args.target, products=args.product, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
