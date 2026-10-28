# RiskSure — Specification

RiskSure is a small, working model of a property & casualty (P&C) insurance policy system for India (amounts in INR). A customer requests a **quote**, the system **rates** it (calculates the price), **underwrites** it (decides whether to accept), and an accepted quote is **bound** (customer commits to buy) and **issued** (becomes a policy).

Products: **Personal Auto**, **Homeowners**, **Small Business** (shop / restaurant / office package).

All data is synthetic and the rates are illustrative. This is not real actuarial pricing.

## Glossary (plain language)
| Term | Meaning |
|---|---|
| Premium | The price the customer pays for one year of cover. |
| Coverage | One thing the policy pays for, e.g. own damage or third-party liability. |
| Sum insured / IDV | The most the insurer will pay out. For cars in India this is the IDV (Insured Declared Value), roughly the car's market value. |
| Rating factor | A characteristic that changes the price, e.g. driver age or city. Each one has a multiplier. |
| Modifier | A discount or surcharge applied after rating, e.g. No Claim Bonus (NCB), a discount for claim-free years. |
| Loading | An extra percentage added by underwriting for higher risk. |
| Underwriting | Deciding whether to accept a risk, and on what terms. |
| Referral | Sending a case to a human underwriter instead of auto-deciding it. |
| Bind / Issue | Bind: the customer accepts the quote. Issue: the policy document and number are created. |

## Architecture
```
React (Vite, Tailwind, Recharts)  ──REST/JSON──►  FastAPI
                                                    ├─ engine/rating.py      generic rating (reads config/*.yaml)
                                                    ├─ engine/scorecard.py   home/business points (config/scorecards.yaml)
                                                    ├─ ml/                   auto claim model + SHAP (models/auto_risk.joblib)
                                                    ├─ engine/rules.py       underwriting rules + impact preview
                                                    ├─ app/assistant.py      English → rule JSON via Claude API (validated)
                                                    └─ SQLAlchemy → SQLite   applicants, quotes, policies, audit, published rules
```
**Config-driven:** everything product-specific (fields, coverages, base rates, rating tables, modifiers, rules, scorecards) lives in `config/`. The engine has no product names or rates in Python. A new product needs only a new YAML file.

## Data model
**Defined in config (YAML, versioned in git)**
- **Product** (`config/<code>.yaml`, marked `kind: product`; validated by `engine/schema.py` on load): `code`, `name`, `version`, `risk` (`method: ml_model` or `scorecard`), `min_premium`, `fields`, `coverages`, `rating_factors`, `modifiers`. Each field has name, label, type (int, float, select, bool), options, min, max, default, help and group (wizard page); the frontend builds its forms from this list.
- **Coverage**: `code`, `name`, `mandatory`, `default` (pre-selected if optional), `basis` (`flat`, `percent_of` or `per_mille_of` a sum-insured field), `rate`.
- **RatingTable** (a `rating_factors` or `modifiers` entry): `name`, `label`, `field`, and a lookup of one of three types:
  - `map`: exact match, e.g. `{1: 1.10, 2: 1.0}`
  - `bands`: `[[upper_bound, multiplier], ...]`, where the first band whose upper bound is ≥ the value applies (the same style as `scorecards.yaml`)
  - `percent_discount`: multiplier = 1 − value/100, used for NCB
- **Rule** (`config/rules.yaml`):
  ```yaml
  - id: young_sports_refer
    product: auto                  # or "*" for all products
    description: Refer drivers under 21 with a sports car
    when:
      all:                         # or "any"
        - {field: driver_age,   op: lt, value: 21}
        - {field: vehicle_type, op: eq, value: sports}
    action: refer                  # decline | refer | load
    load_pct: 0                    # used when action = load
    reason: Young driver with high-performance vehicle
  ```
  Operators: `eq, ne, lt, lte, gt, gte, in, not_in`. Fields can be any applicant field plus `risk_score` and `risk_band`.

**Stored in the database (SQLite)**
- **Applicant**: `id`, `product`, `data` (JSON of the form fields), `source` (`sample` or `manual`), `created_at`.
- **Quote**: `id`, `quote_number`, `product`, `applicant_id`, `status`, `base_premium`, `final_premium`, `breakdown` (JSON steps), `risk_score`, `risk_detail` (SHAP factors or scorecard points), `decision`, `rule_hits` (JSON), `override_premium`, `underwriter_note`, timestamps.
- **Policy**: `id`, `policy_number`, `quote_id`, `product`, `premium`, `start_date`, `end_date` (one year later), `issued_at`.
- **AuditEvent**: `id`, `quote_id`, `action`, `from_status`, `to_status`, `actor`, `detail` (JSON), `timestamp`. One is written for every state change.
- **PublishedRule**: rules approved through the rule assistant: `rule` (JSON), `source_text`, `published_by`, `published_at`. These are stored in the DB because files on the deployed server get wiped on redeploy. The engine merges them with `rules.yaml`.

## Premium formula
```
coverage premium   = rate × exposure                 (e.g. 2% × IDV for auto own damage)
base premium       = sum of selected coverage premiums
rated premium      = base premium × factor_1 × factor_2 × ...   (rating tables)
modified premium   = rated premium × modifier_1 × ...           (NCB, anti-theft, alarm, etc.)
                     floored at the product's minimum premium    (engine/rating.py ends here)
final premium      = modified premium × (1 + total underwriting load %)   (rules engine)
```
Every step is returned as a breakdown row `{step, kind, code, label, detail, value, multiplier, amount_change, running_total}`, and the UI draws it as a waterfall chart. Amounts are rounded at each step, so the bars add up exactly to the premium.

**Calibration:** `engine/calibrate.py` prices every sample applicant and finds one multiplier per product for all coverage rates, so that the loss ratio (claims ÷ premium) on the sample equals `target_loss_ratio` in `config/calibration.yaml` (0.65). The minimum-premium floor is taken into account. The multiplier is written back into the YAML, with each original rate kept in a comment. Rating factors are never changed, so differences between applicants stay as configured. The segment report shows where those factors are wrong.

**Risk score** (separate from rating):
- Auto: a gradient boosting model predicts the probability of a claim next year (0 to 1). SHAP lists the top factors pushing that number up or down.
- Home and Business: points scorecard (0 to 100) and a risk band (low, medium, high, very_high) from `config/scorecards.yaml`.

The score affects price only through underwriting rules, e.g. "risk_score > 0.35 → load 15%". This keeps rating explainable and lets underwriters control how much the model influences decisions.

## Underwriting decisions
| Decision | When |
|---|---|
| `auto_approve` | No rule hit. |
| `approve_adjusted` | Only `load` rules hit; the premium is increased by their loads. |
| `refer` | Any `refer` rule hit, so the case goes to the underwriter queue. |
| `decline` | Any `decline` rule hit. |

Precedence: decline > refer > approve_adjusted > auto_approve. Every rule hit is listed with its human-readable `reason`.
**Impact preview**: run a proposed rule over the sample applicants and report the number affected, the number whose decision changes, and the total and average premium change.

## Quote lifecycle
```
Draft ──rate──► Quoted ──bind──► Bound ──issue──► Issued
  │ │             ▲
  │ └──rate──► Referred ──underwriter approve (optional premium override)──┘
  │               │
  │               └──underwriter decline──► Declined
  └──rate (decision = decline)──────────────► Declined
```
- `rate` sends the quote to Declined if the decision is `decline`, to Referred if it is `refer`, otherwise to Quoted.
- Declined and Issued are final states: nothing can move out of them.
- Invalid transitions (e.g. Draft → Bound) return HTTP 409. Every transition writes an AuditEvent.

## REST endpoints
| Method & path | Purpose |
|---|---|
| `GET /health` | Health check |
| `GET /products`, `GET /products/{code}` | Product list; full config including form fields |
| `POST /rate` | Stateless price + score + decision (used by the what-if simulator, nothing saved) |
| `POST /quotes` | Create applicant + quote and rate it (Draft → Quoted/Referred) |
| `GET /quotes?status=&product=`, `GET /quotes/{id}` | List / detail |
| `POST /quotes/{id}/bind`, `POST /quotes/{id}/issue` | Lifecycle steps (issue creates a Policy) |
| `GET /underwriting/queue` | Referred quotes |
| `POST /quotes/{id}/underwrite` | `{action: approve \| decline, override_premium?, note}` |
| `GET /quotes/{id}/audit` | Audit timeline for one quote |
| `GET /policies`, `GET /policies/{id}` | Issued policies |
| `GET /rules` | Active rules (yaml + published) |
| `POST /rules/preview` | Impact preview of a proposed rule |
| `POST /rules/draft` | English text → validated rule JSON (Claude API, with fallback examples) |
| `POST /rules/publish` | Save an approved rule |
| `GET /dashboard/summary?product=` | Portfolio stats |

**Rule assistant safety:** the AI only turns text into a rule. The result is checked against a strict Pydantic schema (known fields, valid operators, value types). The underwriter sees the impact preview and must approve before anything is published. The API key comes from `ANTHROPIC_API_KEY` and the model name from `ANTHROPIC_MODEL`; neither is ever committed.

## Screens
1. Product picker + quote wizard (forms generated from product config)
2. Quote result: premium waterfall + top risk factors
3. What-if simulator: sliders that re-quote live through `POST /rate`
4. Underwriter queue with approve / override
5. Audit timeline per quote
6. Rules screen with plain-English rule assistant and impact preview
7. Portfolio dashboard with product filter (first to cut if short on time)

## Build roadmap
1. Project setup, SPEC.md, CLAUDE.md
2. Hello-world backend + frontend deployed (Render + Vercel)
3. Auto ML model: train, report AUC, SHAP, save `models/auto_risk.joblib`
4. Product YAMLs + generic rating engine with breakdown + pytest
4b. Rate calibration to a target loss ratio (0.65) on the sample data
5. Rules engine + impact preview + pytest
6. DB models + API for quotes, bind, issue, queue, audit
7. Rule assistant (draft/publish, schema validation, fallback examples)
8. Frontend: (a) picker + wizard, (b) waterfall + what-if, (c) queue, audit, rules, dashboard
9. Seed ~400 demo applicants through the real engines, Dockerfile, README with diagram, final deploy
