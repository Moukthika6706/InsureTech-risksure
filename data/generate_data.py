"""
RiskSure synthetic data generator (Auto, Homeowners, Small Business).
Run:  python generate_data.py
Writes: auto_applicants.csv, home_applicants.csv, business_applicants.csv,
        config/scorecards.yaml
All data is synthetic and illustrative; amounts are in INR (Rs).
Fixed seed => reproducible output.
"""
import os
import numpy as np
import pandas as pd
import yaml

SEED = 42
rng = np.random.default_rng(SEED)
HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(HERE, "..", "config")  # project-root config/, the single source of truth
N_AUTO, N_HOME, N_BUS = 5000, 2500, 1500

def sigmoid(x):
    return 1 / (1 + np.exp(-x))

# city: (tier, relative population weight, flood exposure 0-1)
CITIES = {
    "Mumbai": (1, 12, 0.75), "Delhi": (1, 14, 0.35), "Chennai": (1, 9, 0.75),
    "Bengaluru": (1, 11, 0.35), "Hyderabad": (1, 9, 0.35), "Kolkata": (1, 8, 0.65),
    "Pune": (1, 6, 0.30), "Ahmedabad": (1, 5, 0.25), "Jaipur": (2, 3, 0.20),
    "Lucknow": (2, 3, 0.30), "Kochi": (2, 2, 0.65), "Coimbatore": (2, 2, 0.20),
    "Indore": (2, 2, 0.20), "Chandigarh": (2, 1.5, 0.10), "Nagpur": (2, 2, 0.20),
    "Visakhapatnam": (2, 2, 0.50),
}
CITY_NAMES = list(CITIES)
CITY_P = np.array([CITIES[c][1] for c in CITY_NAMES], dtype=float)
CITY_P /= CITY_P.sum()

def sample_cities(n):
    return rng.choice(CITY_NAMES, n, p=CITY_P)

def tier_of(city):
    return np.array([CITIES[c][0] for c in city])

def flood_exposure(city):
    return np.array([CITIES[c][2] for c in city])

# ---------------------------------------------------------------- scorecards
# Points-based risk scorecards (home, business). Written to config/scorecards.yaml
# so the app and the data use the same single source of truth.
SCORECARDS = {
    "home": {
        "base": 10,
        "min": 0, "max": 100,
        "bands": {"low": 25, "medium": 40, "high": 55},  # upper bounds; above = very_high
        "factors": {
            "roof_type": {"rcc_slab": 0, "tiled": 8, "metal_sheet": 6, "asbestos": 14},
            "construction": {"rcc_frame": 0, "steel": 2, "load_bearing_brick": 8},
            "flood_zone": {1: 0, 2: 12, 3: 25},
            "building_age_years": [[10, 0], [25, 5], [40, 10], [200, 16]],
            "fire_station_km": [[2, 0], [5, 4], [10, 9], [100, 15]],
            "prior_claims": {"per_claim": 8, "max_claims_counted": 3},
            "security": {"alarm": -4, "cctv": -3, "gated_community": -5},
            "occupancy": {"owner_occupied": 0, "rented_out": 6},
        },
    },
    "business": {
        "base": 8,
        "min": 0, "max": 100,
        "bands": {"low": 25, "medium": 40, "high": 55},
        "factors": {
            "business_type": {
                "it_office": 2, "clinic": 6, "retail_shop": 8, "salon": 8,
                "hotel_guesthouse": 12, "warehouse": 16, "restaurant": 18,
                "manufacturing_unit": 20,
            },
            "flood_zone": {1: 0, 2: 10, 3: 20},
            "building_age_years": [[10, 0], [25, 5], [40, 10], [200, 15]],
            "staff_count": [[10, 0], [50, 4], [200, 8], [100000, 12]],
            "prior_claims": {"per_claim": 8, "max_claims_counted": 3},
            "fire_safety_certificate": {True: -6, False: 0},
            "sprinklers": {True: -6, False: 0},
            "handles_cash": {True: 4, False: 0},
        },
    },
}

def band_points(value, bands):
    for upper, pts in bands:
        if value <= upper:
            return pts
    return bands[-1][1]

def risk_band(score, cfg):
    b = cfg["bands"]
    if score <= b["low"]:
        return "low"
    if score <= b["medium"]:
        return "medium"
    if score <= b["high"]:
        return "high"
    return "very_high"

def score_home(r):
    f = SCORECARDS["home"]["factors"]
    s = SCORECARDS["home"]["base"]
    s += f["roof_type"][r["roof_type"]]
    s += f["construction"][r["construction"]]
    s += f["flood_zone"][int(r["flood_zone"])]
    s += band_points(r["building_age_years"], f["building_age_years"])
    s += band_points(r["fire_station_km"], f["fire_station_km"])
    pc = f["prior_claims"]
    s += pc["per_claim"] * min(int(r["prior_claims_5y"]), pc["max_claims_counted"])
    s += f["security"]["alarm"] * int(r["has_alarm"])
    s += f["security"]["cctv"] * int(r["has_cctv"])
    s += f["security"]["gated_community"] * int(r["gated_community"])
    s += f["occupancy"][r["occupancy"]]
    return int(np.clip(s, 0, 100))

def score_business(r):
    f = SCORECARDS["business"]["factors"]
    s = SCORECARDS["business"]["base"]
    s += f["business_type"][r["business_type"]]
    s += f["flood_zone"][int(r["flood_zone"])]
    s += band_points(r["building_age_years"], f["building_age_years"])
    s += band_points(r["staff_count"], f["staff_count"])
    pc = f["prior_claims"]
    s += pc["per_claim"] * min(int(r["prior_claims_5y"]), pc["max_claims_counted"])
    s += f["fire_safety_certificate"][bool(r["fire_safety_certificate"])]
    s += f["sprinklers"][bool(r["sprinklers"])]
    s += f["handles_cash"][bool(r["handles_cash"])]
    return int(np.clip(s, 0, 100))

# ---------------------------------------------------------------------- AUTO
def gen_auto(n):
    city = sample_cities(n)
    tier = tier_of(city)
    age = np.clip(rng.normal(36, 11, n), 18, 80).round().astype(int)
    years_licensed = np.clip(age - 18 - rng.integers(0, 7, n), 0, None)
    vtype = rng.choice(["hatchback", "sedan", "suv", "mpv", "ev", "sports"], n,
                       p=[0.35, 0.20, 0.25, 0.10, 0.06, 0.04])
    vehicle_age = np.clip(rng.gamma(2.2, 2.2, n), 0, 18).round().astype(int)
    annual_km = np.clip(rng.normal(11000, 5000, n), 2000, 40000)
    annual_km = (np.round(annual_km / 500) * 500).astype(int)
    prior_claims = np.clip(rng.poisson(0.22 + 0.15 * (age < 25), n), 0, 4)
    base_price = {"hatchback": 650000, "sedan": 1100000, "suv": 1600000,
                  "mpv": 1400000, "ev": 1800000, "sports": 3500000}
    idv = np.array([base_price[v] for v in vtype]) * (0.9 ** vehicle_age) \
          * rng.lognormal(0, 0.18, n)
    idv = (np.round(idv / 5000) * 5000).astype(int)
    ncb_by_years = np.select([years_licensed < 1, years_licensed < 2, years_licensed < 3,
                              years_licensed < 4, years_licensed < 5],
                             [0, 20, 25, 35, 45], default=50)
    ncb = np.where(prior_claims > 0, 0, ncb_by_years)
    parking = rng.choice(["garage", "street"], n, p=[0.55, 0.45])
    anti_theft = rng.random(n) < 0.35

    vtype_eff = {"sports": 0.70, "suv": 0.10, "hatchback": 0.05, "mpv": 0.0,
                 "sedan": 0.0, "ev": -0.10}
    logit = (-2.75
             + 0.90 * (age < 25) + 0.30 * ((age >= 25) & (age < 30)) + 0.50 * (age > 65)
             + 0.45 * prior_claims
             + np.array([vtype_eff[v] for v in vtype])
             + 0.00003 * (annual_km - 11000)
             + 0.15 * (vehicle_age > 10)
             + 0.35 * (tier == 1)
             + 0.20 * (parking == "street")
             - 0.25 * anti_theft
             - 0.015 * years_licensed
             + rng.normal(0, 0.45, n))
    p_claim = sigmoid(logit)
    claim = rng.binomial(1, p_claim)
    sev = np.minimum(rng.lognormal(np.log(28000), 0.85, n), 0.8 * idv)
    claim_amount = np.where(claim == 1, (np.round(sev / 100) * 100), 0).astype(int)

    return pd.DataFrame({
        "applicant_id": [f"AUT-{i:05d}" for i in range(1, n + 1)],
        "driver_age": age, "years_licensed": years_licensed, "city": city,
        "city_tier": tier, "vehicle_type": vtype, "vehicle_age_years": vehicle_age,
        "insured_declared_value_inr": idv, "annual_km": annual_km,
        "prior_claims_3y": prior_claims, "no_claim_bonus_pct": ncb,
        "parking": parking, "anti_theft_device": anti_theft,
        "had_claim_next_year": claim, "claim_amount_inr": claim_amount,
    })

# ---------------------------------------------------------------------- HOME
def gen_home(n):
    city = sample_cities(n)
    tier = tier_of(city)
    area = np.clip(rng.normal(1100, 420, n), 400, 4000).round(-1).astype(int)
    price_sqft = np.where(tier == 1, rng.uniform(9000, 18000, n), rng.uniform(4500, 8000, n))
    home_value = (np.round(area * price_sqft / 10000) * 10000).astype(int)
    age_years = np.clip(rng.gamma(2.0, 9.0, n), 0, 50).round().astype(int)
    build_year = 2026 - age_years

    roof, constr, flood = [], [], []
    fe = flood_exposure(city)
    for a, e in zip(age_years, fe):
        old = a > 25
        roof.append(rng.choice(["rcc_slab", "tiled", "metal_sheet", "asbestos"],
                               p=[0.50, 0.20, 0.14, 0.16] if old else [0.78, 0.09, 0.10, 0.03]))
        constr.append(rng.choice(["rcc_frame", "load_bearing_brick", "steel"],
                                 p=[0.35, 0.60, 0.05] if old else [0.70, 0.27, 0.03]))
        flood.append(rng.choice([1, 2, 3], p=_flood_p(e)))
    fire_km = np.clip(rng.exponential(3.5, n), 0.3, 25).round(1)
    gated = rng.random(n) < np.where(tier == 1, 0.45, 0.25)
    alarm = rng.random(n) < 0.22
    cctv = rng.random(n) < 0.40
    prior = np.clip(rng.poisson(0.12, n), 0, 3)
    occ = rng.choice(["owner_occupied", "rented_out"], n, p=[0.82, 0.18])
    sum_insured = (np.round(home_value * rng.uniform(0.70, 1.0, n) / 10000) * 10000).astype(int)
    contents = (np.round(rng.uniform(0.05, 0.18, n) * home_value / 10000) * 10000).astype(int)

    df = pd.DataFrame({
        "applicant_id": [f"HOM-{i:05d}" for i in range(1, n + 1)],
        "city": city, "city_tier": tier, "area_sqft": area,
        "home_value_inr": home_value, "build_year": build_year,
        "building_age_years": age_years, "roof_type": roof, "construction": constr,
        "flood_zone": flood, "fire_station_km": fire_km, "gated_community": gated,
        "has_alarm": alarm, "has_cctv": cctv, "prior_claims_5y": prior,
        "occupancy": occ, "building_sum_insured_inr": sum_insured,
        "contents_sum_insured_inr": contents,
    })
    df["scorecard_points"] = df.apply(score_home, axis=1)
    df["risk_band"] = df["scorecard_points"].apply(lambda s: risk_band(s, SCORECARDS["home"]))
    logit = -4.6 + 0.055 * df["scorecard_points"].values + rng.normal(0, 0.5, n)
    claim = rng.binomial(1, sigmoid(logit))
    sev = np.minimum(rng.lognormal(np.log(0.04 * home_value + 30000), 0.8), 0.6 * sum_insured)
    df["had_claim_next_year"] = claim
    df["claim_amount_inr"] = np.where(claim == 1, (np.round(sev / 1000) * 1000), 0).astype(int)
    return df

def _flood_p(e):
    p3 = 0.02 + 0.30 * e
    p2 = 0.08 + 0.35 * e
    return [1 - p2 - p3, p2, p3]

# ------------------------------------------------------------------ BUSINESS
BTYPES = ["it_office", "clinic", "retail_shop", "salon", "hotel_guesthouse",
          "warehouse", "restaurant", "manufacturing_unit"]
BTYPE_P = [0.10, 0.10, 0.28, 0.12, 0.05, 0.08, 0.20, 0.07]
STAFF_MED = {"it_office": 40, "clinic": 8, "retail_shop": 6, "salon": 5,
             "hotel_guesthouse": 20, "warehouse": 15, "restaurant": 14,
             "manufacturing_unit": 60}
REV_PER_STAFF = {"it_office": 2_400_000, "clinic": 1_800_000, "retail_shop": 1_500_000,
                 "salon": 600_000, "hotel_guesthouse": 900_000, "warehouse": 1_300_000,
                 "restaurant": 800_000, "manufacturing_unit": 1_600_000}
CASH_P = {"it_office": 0.02, "clinic": 0.4, "retail_shop": 0.75, "salon": 0.7,
          "hotel_guesthouse": 0.5, "warehouse": 0.1, "restaurant": 0.7,
          "manufacturing_unit": 0.1}

def gen_business(n):
    city = sample_cities(n)
    tier = tier_of(city)
    btype = rng.choice(BTYPES, n, p=BTYPE_P)
    staff = np.array([max(1, int(rng.lognormal(np.log(STAFF_MED[b]), 0.6))) for b in btype])
    revenue = np.array([s * REV_PER_STAFF[b] * rng.lognormal(0, 0.3)
                        for s, b in zip(staff, btype)])
    revenue = (np.round(revenue / 100000) * 100000).astype(int)
    age_years = np.clip(rng.gamma(2.0, 9.0, n), 0, 50).round().astype(int)
    sqft = np.clip(staff * rng.uniform(60, 140, n) + rng.normal(300, 100, n), 250, 60000)
    sqft = (np.round(sqft / 10) * 10).astype(int)
    fe = flood_exposure(city)
    flood = [rng.choice([1, 2, 3], p=_flood_p(e)) for e in fe]
    prior = np.clip(rng.poisson(0.2, n), 0, 3)
    fire_cert = rng.random(n) < 0.60
    sprink = rng.random(n) < np.where(staff > 50, 0.45, 0.12)
    cash = np.array([rng.random() < CASH_P[b] for b in btype])
    stock_share = {"retail_shop": 0.25, "warehouse": 0.6, "restaurant": 0.04,
                   "manufacturing_unit": 0.3, "salon": 0.05, "clinic": 0.05,
                   "hotel_guesthouse": 0.03, "it_office": 0.0}
    stock = np.array([r * stock_share[b] * rng.uniform(0.5, 1.2) for r, b in zip(revenue, btype)])
    stock = (np.round(stock / 100000) * 100000).astype(int)
    prop_si = (np.round((sqft * np.where(tier == 1, 6000, 3500) * rng.uniform(0.6, 1.0, n)) / 100000) * 100000).astype(int)

    df = pd.DataFrame({
        "applicant_id": [f"BUS-{i:05d}" for i in range(1, n + 1)],
        "business_type": btype, "city": city, "city_tier": tier,
        "staff_count": staff, "annual_revenue_inr": revenue,
        "premises_sqft": sqft, "building_age_years": age_years,
        "flood_zone": flood, "prior_claims_5y": prior,
        "fire_safety_certificate": fire_cert, "sprinklers": sprink,
        "handles_cash": cash, "stock_value_inr": stock,
        "property_sum_insured_inr": prop_si,
        "liability_limit_inr": rng.choice([2_500_000, 5_000_000, 10_000_000, 20_000_000], n,
                                          p=[0.35, 0.35, 0.2, 0.1]),
    })
    df["scorecard_points"] = df.apply(score_business, axis=1)
    df["risk_band"] = df["scorecard_points"].apply(lambda s: risk_band(s, SCORECARDS["business"]))
    logit = -4.4 + 0.058 * df["scorecard_points"].values + rng.normal(0, 0.5, n)
    claim = rng.binomial(1, sigmoid(logit))
    sev = np.minimum(rng.lognormal(np.log(0.01 * revenue + 80000), 0.9), 0.7 * prop_si)
    df["had_claim_next_year"] = claim
    df["claim_amount_inr"] = np.where(claim == 1, (np.round(sev / 1000) * 1000), 0).astype(int)
    return df

# ---------------------------------------------------------------------- main
if __name__ == "__main__":
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(os.path.join(CONFIG_DIR, "scorecards.yaml"), "w") as fh:
        yaml.safe_dump(SCORECARDS, fh, sort_keys=False)

    auto, home, bus = gen_auto(N_AUTO), gen_home(N_HOME), gen_business(N_BUS)
    auto.to_csv(os.path.join(HERE, "auto_applicants.csv"), index=False)
    home.to_csv(os.path.join(HERE, "home_applicants.csv"), index=False)
    bus.to_csv(os.path.join(HERE, "business_applicants.csv"), index=False)

    for name, df in [("auto", auto), ("home", home), ("business", bus)]:
        print(f"{name}: {len(df)} rows, claim rate {df['had_claim_next_year'].mean():.1%}")
