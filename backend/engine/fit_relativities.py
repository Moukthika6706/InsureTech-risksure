"""Fit rating-factor multipliers ("relativities") from the sample claims.

How it works, per product:
  1. Price every applicant with the current config and take its EXPOSURE:
     the premium before rating factors (coverage premiums x modifiers). Premium
     is exposure x factors, so we model claims per rupee of exposure and the
     fitted factors plug straight back into the same formula.
  2. Turn each rating factor into one 0/1 column per level, using exactly the
     YAML bands / map keys, dropping one reference level per factor.
  3. Fit a Tweedie GLM with a log link: log(E[claim / exposure]) = b0 + sum(b_level).
     A log link makes effects multiply, so each level's multiplier is exp(b).
     Tweedie (power ~1.5) suits insurance losses: most policies have zero
     claims, the rest have a positive, skewed amount.
  4. Safeguards: blend thin levels toward 1.0 (credibility), force ordered
     factors to be non-decreasing, re-base the reference level to 1.0, cap.

Run from backend/:
    python -m engine.fit_relativities [--product home]           # proposal only
    python -m engine.fit_relativities --write --product home     # write + recalibrate
"""
import argparse
import math
import re
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import TweedieRegressor

from engine import calibrate as cal
from engine.config import CONFIG_DIR, load_products, read_yaml
from engine.rating import rate
from engine.schema import Lookup, Product, norm_key

DATA_DIR = CONFIG_DIR.parent / "data"
FIT_TOLERANCE = 0.005   # changes under 0.5% count as "already fitted"


# ---------------------------------------------------------------- levels

def level_labels(table: Lookup) -> list[str]:
    if table.type == "bands":
        labels, prev = [], None
        for upper, _ in table.bands:
            labels.append(f"<= {upper:g}" if prev is None else f"{prev:g} - {upper:g}")
            prev = upper
        return labels
    return [str(k) for k in table.values]


def current_multipliers(table: Lookup) -> list[float]:
    return [m for _, m in table.bands] if table.type == "bands" else list(table.values.values())


def level_index(table: Lookup, value) -> int:
    """Which level of the table a value falls in (same rules as the rating engine)."""
    if table.type == "bands":
        for i, (upper, _) in enumerate(table.bands):
            if value <= upper:
                return i
        return len(table.bands) - 1
    for i, k in enumerate(table.values):
        if norm_key(k) == norm_key(value):
            return i
    raise ValueError(f"{table.name}: value {value!r} has no level")


def exposures(product: Product, df: pd.DataFrame) -> np.ndarray:
    """Premium before rating factors: coverage premiums x modifiers (pre-floor)."""
    out = []
    for row in df.to_dict("records"):
        steps = rate(product, row)["steps"]
        base = sum(s["amount_change"] for s in steps if s["kind"] == "coverage")
        mods = math.prod(s["multiplier"] for s in steps if s["kind"] == "modifier")
        out.append(base * mods)
    return np.array(out)


# ------------------------------------------------------------------- fit

def fit_product(product: Product, df: pd.DataFrame, claims: np.ndarray, fit_cfg: dict) -> pd.DataFrame:
    """Return one row per (factor, level) with current, raw fitted and proposed multipliers."""
    exposure = exposures(product, df)
    power = fit_cfg["tweedie_power"]
    has_claim = claims > 0

    # Design matrix: one 0/1 column per non-reference level.
    columns, meta = [], []
    for t in product.rating_factors:
        idx = np.array([level_index(t, v) for v in df[t.field]])
        cur = current_multipliers(t)
        counts = np.bincount(idx, minlength=len(cur))
        # Reference (base) level = the level with the most policies. It must not
        # depend on the current multipliers, or re-fitting would give new answers.
        ref = int(np.argmax(counts))
        for i, label in enumerate(level_labels(t)):
            meta.append({"factor": t.name, "level": label, "level_no": i, "current": cur[i],
                         "policies": int(counts[i]), "claims": int(has_claim[idx == i].sum()),
                         "reference": i == ref, "col": None})
            if i != ref and counts[i] > 0:
                meta[-1]["col"] = len(columns)
                columns.append((idx == i).astype(float))
    X = np.column_stack(columns)

    # Claims per rupee of exposure, weighted by exposure^(2-p): for a Tweedie
    # model this is exactly equivalent to using log(exposure) as an offset.
    y = claims / exposure
    glm = TweedieRegressor(power=power, link="log", alpha=fit_cfg["alpha"], max_iter=5000, tol=1e-8)
    glm.fit(X, y, sample_weight=exposure ** (2 - power))

    rows = pd.DataFrame(meta)
    rows["fitted"] = [1.0 if pd.isna(r.col) else math.exp(glm.coef_[int(r.col)])
                      for r in rows.itertuples()]
    rows.loc[rows["policies"] == 0, "fitted"] = np.nan
    return apply_safeguards(rows, product.code, fit_cfg)


def apply_safeguards(rows: pd.DataFrame, code: str, fit_cfg: dict) -> pd.DataFrame:
    full = fit_cfg["full_credibility_claims"]
    lo, hi = fit_cfg["cap"]
    monotonic = set(fit_cfg.get("monotonic_increasing", {}).get(code, []))
    rows = rows.copy()
    rows["credibility"] = np.minimum(1.0, np.sqrt(rows["claims"] / full))
    rows["notes"] = ""

    out = []
    for name, g in rows.groupby("factor", sort=False):
        g = g.copy()
        has_data = g["policies"] > 0
        # 1. Credibility: shrink log-multiplier toward 0 (i.e. multiplier toward 1.0).
        log_m = np.log(g["fitted"].where(has_data, 1.0)) * g["credibility"]
        g.loc[g["claims"] < full, "notes"] += "low credibility; "
        # 2. Ordered factors: isotonic (pool-adjacent-violators) fit in log space.
        if name in monotonic and has_data.sum() > 1:
            iso = IsotonicRegression(increasing=True)
            fixed = iso.fit_transform(g.loc[has_data, "level_no"], log_m[has_data],
                                      sample_weight=g.loc[has_data, "claims"] + 1)
            changed = np.abs(fixed - log_m[has_data]) > 1e-9
            g.loc[g.index[has_data][changed], "notes"] += "order enforced; "
            log_m[has_data] = fixed
        # 3. Re-base so the reference level is exactly 1.0, then 4. cap.
        m = np.exp(log_m - log_m[g["reference"]].iloc[0])
        capped = (m < lo) | (m > hi)
        g.loc[capped, "notes"] += "capped; "
        m = m.clip(lo, hi)
        # Levels with no sample data keep their current multiplier.
        g["proposed"] = np.where(has_data, m.round(3), g["current"])
        g.loc[~has_data, "notes"] += "no data, kept current; "
        g.loc[g["reference"], "notes"] += "reference; "
        out.append(g)
    result = pd.concat(out)
    result["notes"] = result["notes"].str.rstrip("; ")
    return result.drop(columns=["col"])


# ------------------------------------------------------------ projection

def with_multipliers(product: Product, rows: pd.DataFrame) -> Product:
    """A copy of the product with proposed multipliers (in memory only)."""
    new = product.model_copy(deep=True)
    for t in new.rating_factors:
        m = rows.loc[rows["factor"] == t.name].sort_values("level_no")["proposed"].tolist()
        if t.type == "bands":
            t.bands = [(upper, float(x)) for (upper, _), x in zip(t.bands, m)]
        else:
            t.values = {k: float(x) for k, x in zip(t.values, m)}
    return new


def project(product: Product, proposed: Product, df: pd.DataFrame, claims, settings) -> dict:
    """Recalibrate both versions to target and compare segment loss ratios."""
    target = settings["target_loss_ratio"]
    out = {}
    for name, p in (("current", product), ("proposed", proposed)):
        raw = cal.price_portfolio(p, df)
        k = cal.solve_multiplier(raw, p.min_premium, claims.sum(), target)
        out[name] = cal.floored(raw, k, p.min_premium)
    segs = {s["name"]: cal.segment_table(df, claims, out["current"], out["proposed"], s, target,
                                         settings["flag_points"], settings.get("min_claims_for_flag", 0))
            for s in settings["segments"].get(product.code, [])}
    return {"premiums": out, "segments": segs}


# ------------------------------------------------------------------ main

def propose(config_dir: Path = CONFIG_DIR, data_dir: Path = DATA_DIR,
            products: list[str] = None, verbose: bool = True) -> dict:
    settings = read_yaml(Path(config_dir) / "calibration.yaml")
    all_products = load_products(Path(config_dir))
    results = {}
    for code in products or sorted(all_products):
        product = all_products[code]
        df = pd.read_csv(Path(data_dir) / settings["data_file"].format(code=code))
        claims = df[settings["claims_column"]].to_numpy(dtype=float)
        rows = fit_product(product, df, claims, settings["fitting"])
        proj = project(product, with_multipliers(product, rows), df, claims, settings)
        results[code] = {"rows": rows, **proj}
        if verbose:
            print_proposal(product, rows, proj)
    return results


def print_proposal(product: Product, rows: pd.DataFrame, proj: dict):
    print(f"\n=== {product.name} ({product.code}) — proposed rating factors ===")
    show = rows[["factor", "level", "current", "fitted", "proposed", "claims", "policies", "notes"]].copy()
    show["fitted"] = show["fitted"].map(lambda x: "-" if pd.isna(x) else f"{x:.3f}")
    print(show.to_string(index=False))
    for name, t in proj["segments"].items():
        s = t[["policies", "n_claims", "lr_before", "lr_after", "flag"]].copy()
        s.columns = ["policies", "claims", "LR current", "LR proposed", "flag"]
        for c in ("LR current", "LR proposed"):
            s[c] = s[c].map(cal.pct)
        print(f"\n  Projected loss ratio by {name} (both recalibrated to target):")
        print("  " + s.to_string().replace("\n", "\n  "))


# ----------------------------------------------------------- YAML update

def _num(x: float) -> str:
    """Multiplier text: 1.0 -> '1.0', 0.6904 -> '0.69'."""
    s = f"{x:.3f}".rstrip("0")
    return s + "0" if s.endswith(".") else s


def _upper(x: float) -> str:
    """Band bound text: 5.0 -> '5', 1000000.0 -> '1000000' (never 1e+06), 2.5 -> '2.5'."""
    return str(int(x)) if float(x).is_integer() else repr(float(x))


def _key(k) -> str:
    return str(k).lower() if isinstance(k, bool) else str(k)


def table_text(t: Lookup) -> str:
    if t.type == "bands":
        return "bands: [" + ", ".join(f"[{_upper(u)}, {_num(m)}]" for u, m in t.bands) + "]"
    return "values: {" + ", ".join(f"{_key(k)}: {_num(m)}" for k, m in t.values.items()) + "}"


TABLE_LINE = re.compile(r"^(\s+)(values|bands):\s*(.*)$")
FIT_TAG = "#[fit]"   # every header line carries this tag so a re-run can replace it whole


def _unclosed(text: str) -> bool:
    return text.count("{") + text.count("[") > text.count("}") + text.count("]")


def write_factors(path: Path, fitted: Product, fit_cfg: dict, today: str):
    """Replace each rating factor's values/bands line(s) in the YAML text.

    The pre-fit table is kept once as a `# pre-fit:` comment above the new line,
    and a header above `rating_factors:` records the method and date.
    """
    tables = {t.name: t for t in fitted.rating_factors}
    lines = path.read_text(encoding="utf-8").splitlines()
    out, section, current, i = [], None, None, 0
    while i < len(lines):
        line = lines[i]
        if line and not line[0].isspace() and not line.startswith(("#", "-")):
            section = line.split(":")[0]
        name = re.match(r"^\s*- name:\s*(\S+)", line)
        if section == "rating_factors" and name:
            current = name.group(1)
        m = TABLE_LINE.match(line)
        if section == "rating_factors" and current in tables and m:
            old = [line]
            while _unclosed(" ".join(old)):    # a {..} or [..] table spread over several lines
                i += 1
                old.append(lines[i])
            indent = m.group(1)
            if not (out and out[-1].strip().startswith("# pre-fit:")):
                flat = " ".join(l.strip() for l in old).split(":", 1)[1].strip()
                out.append(f"{indent}# pre-fit: {flat}")
            out.append(indent + table_text(tables[current]))
            current = None
        else:
            out.append(line)
        i += 1

    out = [l for l in out if not l.startswith(FIT_TAG)]   # drop the whole old header
    at = next(n for n, l in enumerate(out) if l.startswith("rating_factors:"))
    lo, hi = fit_cfg["cap"]
    out[at:at] = [
        f"{FIT_TAG} FITTED on the synthetic sample (data/{path.stem}_applicants.csv) on {today}:",
        f"{FIT_TAG} Tweedie GLM, log link, power {fit_cfg['tweedie_power']:g}, claims per rupee of pre-factor premium.",
        f"{FIT_TAG} Levels with <{fit_cfg['full_credibility_claims']} claims blended toward 1.0; ordered factors "
        f"non-decreasing; capped to [{lo:g}, {hi:g}].",
        f"{FIT_TAG} Illustrative only — not real actuarial pricing.",
    ]
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def apply(config_dir: Path = CONFIG_DIR, data_dir: Path = DATA_DIR,
          products: list[str] = None, verbose: bool = True) -> dict:
    """Fit, write the multipliers to YAML, recalibrate base rates, report before/after."""
    config_dir = Path(config_dir)
    settings = read_yaml(config_dir / "calibration.yaml")
    products = products or sorted(load_products(config_dir))
    before = cal.calibrate(config_dir, data_dir, products=products, dry_run=True, verbose=False)
    fits = propose(config_dir, data_dir, products=products, verbose=False)
    today = date.today().isoformat()
    for code in products:
        rows = fits[code]["rows"]
        # Skip re-writes that would only move multipliers by rounding noise.
        fits[code]["written"] = bool((abs(rows["proposed"] / rows["current"] - 1) > FIT_TOLERANCE).any())
        if fits[code]["written"]:
            fitted = with_multipliers(load_products(config_dir)[code], rows)
            write_factors(config_dir / f"{code}.yaml", fitted, settings["fitting"], today)
    load_products.cache_clear()
    recal = cal.calibrate(config_dir, data_dir, products=products, verbose=False)
    after = cal.calibrate(config_dir, data_dir, products=products, dry_run=True, verbose=False)
    if verbose:
        print_before_after(before, recal, after, settings)
    return {"before": before, "recalibration": recal, "after": after, "fits": fits}


def print_before_after(before: dict, recal: dict, after: dict, settings: dict):
    min_claims = settings.get("min_claims_for_flag", 0)
    for code in before:
        b, a = before[code], after[code]
        print(f"\n=== {b['name']}: portfolio loss ratio {cal.pct(b['lr_before'])} -> "
              f"{cal.pct(a['lr_before'])}; base rates recalibrated x{recal[code]['multiplier']:.4f}")
        for name in b["segments"]:
            tb, ta = b["segments"][name], a["segments"][name]
            t = pd.DataFrame({"policies": tb["policies"], "claims": tb["n_claims"],
                              "LR before": tb["lr_before"].map(cal.pct),
                              "LR after": ta["lr_before"].map(cal.pct)})
            target = settings["target_loss_ratio"]
            off = (ta["lr_before"] - target).abs() * 100 > settings["flag_points"]
            t["check"] = np.where(tb["n_claims"] < min_claims, f"ignored (<{min_claims} claims)",
                                  np.where(off, f">{settings['flag_points']} pts off", "ok"))
            print(f"  Loss ratio by {name}:")
            print("  " + t.to_string().replace("\n", "\n  "))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--product", action="append", help="only this product (repeatable)")
    ap.add_argument("--write", action="store_true", help="write to YAML and recalibrate")
    args = ap.parse_args()
    if args.write:
        if not args.product:
            ap.error("--write needs explicit --product (approve each product's changes)")
        apply(products=args.product)
    else:
        propose(products=args.product)


if __name__ == "__main__":
    main()
