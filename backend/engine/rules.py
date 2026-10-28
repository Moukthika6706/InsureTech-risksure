"""Underwriting rules engine — plain, testable code (no AI).

A rule says WHEN (conditions on applicant fields, risk_score, risk_band) and
WHAT (decline, refer to an underwriter, or load the premium by a %). Rules
live in config/rules.yaml; rules published from the assistant (Step 7) are
passed in the same format and merged.

Decision precedence: decline > refer > approve_adjusted (loads) > auto_approve.
"""
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from engine.config import CONFIG_DIR, load_products, read_yaml
from engine.schema import Product, norm_key

BANDS = ["low", "medium", "high", "very_high"]          # ordered, so "risk_band gte high" works
RISK_FIELDS = {"risk_score", "risk_band"}
NUMERIC_OPS = {"lt", "lte", "gt", "gte"}
LIST_OPS = {"in", "not_in"}
LOAD_RANGE = (-50, 300)                                  # a credit of up to 50%, a load of up to 300%


class RuleError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


# ---------------------------------------------------------------- schema

class Condition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: str
    op: Literal["eq", "ne", "lt", "lte", "gt", "gte", "in", "not_in"]
    value: Any


class Group(BaseModel):
    """Exactly one of `all` (every condition true) or `any` (at least one)."""
    model_config = ConfigDict(extra="forbid")
    all: Optional[list[Union["Group", Condition]]] = None
    any: Optional[list[Union["Group", Condition]]] = None

    @model_validator(mode="after")
    def one_kind(self):
        if (self.all is None) == (self.any is None):
            raise ValueError("a condition group needs exactly one of 'all' or 'any'")
        if not (self.all or self.any):
            raise ValueError("a condition group cannot be empty")
        return self

    @property
    def items(self):
        return self.all if self.all is not None else self.any


Group.model_rebuild()   # resolve the self-reference (groups can nest)


class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[a-z0-9_]{3,60}$")
    product: str                                         # product code, or "*" for every product
    description: str = Field(min_length=3)
    when: Group
    action: Literal["decline", "refer", "load"]
    load_pct: float = 0
    reason: str = Field(min_length=3)                    # shown to underwriters and in the audit trail
    enabled: bool = True

    @model_validator(mode="after")
    def load_matches_action(self):
        lo, hi = LOAD_RANGE
        if self.action == "load" and not (self.load_pct != 0 and lo <= self.load_pct <= hi):
            raise ValueError(f"a load rule needs load_pct between {lo} and {hi} (not 0)")
        if self.action != "load" and self.load_pct != 0:
            raise ValueError("load_pct is only allowed when action is 'load'")
        return self

    def as_dict(self) -> dict:
        """Plain dict without empty fields (no "any": null next to "all")."""
        return self.model_dump(exclude_none=True)


# ------------------------------------------------------------ validation

def _value_errors(product: Product, field: str, op: str, value) -> list[str]:
    """Check one condition's value makes sense for the field's type."""
    where = f"{product.code}.{field}"
    if op in LIST_OPS:
        if not isinstance(value, list) or not value:
            return [f"{where}: '{op}' needs a non-empty list"]
        return [e for v in value for e in _value_errors(product, field, "eq", v)]
    if isinstance(value, list):
        return [f"{where}: '{op}' needs a single value, not a list"]

    if field == "risk_band":
        return [] if norm_key(value) in BANDS else [f"{where}: must be one of {BANDS}"]
    kind = "float" if field == "risk_score" else product.field(field).type
    if op in NUMERIC_OPS and kind not in ("int", "float"):
        return [f"{where}: '{op}' only works on numbers, and {field} is a {kind}"]
    if kind in ("int", "float"):
        ok = isinstance(value, (int, float)) and not isinstance(value, bool)
        return [] if ok else [f"{where}: value must be a number"]
    if kind == "bool":
        return [] if norm_key(value) in ("true", "false") else [f"{where}: value must be true or false"]
    options = [o.value for o in product.field(field).options]
    return [] if norm_key(value) in {norm_key(o) for o in options} else [f"{where}: must be one of {options}"]


def _conditions(group: Group):
    for item in group.items:
        yield from (_conditions(item) if isinstance(item, Group) else [item])


def check_rule(rule: Rule, products: dict[str, Product]) -> list[str]:
    """Semantic checks against the product configs (fields exist, values valid)."""
    if rule.product != "*" and rule.product not in products:
        return [f"unknown product '{rule.product}' (known: {sorted(products)} or '*')"]
    targets = list(products.values()) if rule.product == "*" else [products[rule.product]]
    errors = []
    for c in _conditions(rule.when):
        for p in targets:
            if c.field not in RISK_FIELDS and c.field not in {f.name for f in p.fields}:
                errors.append(f"{p.code}: unknown field '{c.field}'")
            else:
                errors += _value_errors(p, c.field, c.op, c.value)
    return list(dict.fromkeys(errors))   # de-duplicate, keep order


def parse_rule(raw: dict, products: dict[str, Product] = None) -> Rule:
    """Validate a rule dict (from YAML, the API or the AI assistant). Raises RuleError."""
    products = products or load_products()
    try:
        rule = Rule.model_validate(raw)
    except ValidationError as e:
        raise RuleError([f"{'.'.join(map(str, err['loc'])) or 'rule'}: {err['msg']}"
                         for err in e.errors()]) from e
    errors = check_rule(rule, products)
    if errors:
        raise RuleError(errors)
    return rule


@lru_cache(maxsize=None)
def load_rules(config_dir: Path = CONFIG_DIR) -> tuple[Rule, ...]:
    raw = read_yaml(Path(config_dir) / "rules.yaml")
    products = load_products(Path(config_dir))
    rules, errors = [], []
    for i, r in enumerate(raw.get("rules", [])):
        try:
            rules.append(parse_rule(r, products))
        except RuleError as e:
            errors += [f"rule #{i + 1} ({r.get('id', '?')}): {m}" for m in e.errors]
    ids = [r.id for r in rules]
    errors += [f"duplicate rule id '{i}'" for i in sorted({i for i in ids if ids.count(i) > 1})]
    if errors:
        raise RuleError(errors)
    return tuple(rules)


# ------------------------------------------------------------ evaluation

def _compare(field: str, op: str, actual, expected) -> bool:
    if op in LIST_OPS:
        found = norm_key(actual) in {norm_key(v) for v in expected}
        return found if op == "in" else not found
    if field == "risk_band":                       # compare bands by their order
        actual, expected = BANDS.index(norm_key(actual)), BANDS.index(norm_key(expected))
    if op == "eq":
        return norm_key(actual) == norm_key(expected)
    if op == "ne":
        return norm_key(actual) != norm_key(expected)
    a, e = float(actual), float(expected)
    return {"lt": a < e, "lte": a <= e, "gt": a > e, "gte": a >= e}[op]


def matches(group: Group, facts: dict) -> bool:
    results = (matches(i, facts) if isinstance(i, Group) else _compare(i.field, i.op, facts[i.field], i.value)
               for i in group.items)
    return all(results) if group.all is not None else any(results)


def rules_for(product_code: str, rules) -> list[Rule]:
    return [r for r in rules if r.enabled and r.product in (product_code, "*")]


def decide(hits: list[Rule]) -> tuple[str, float]:
    """(decision, total load %) from the rules that fired."""
    total_load = sum(r.load_pct for r in hits if r.action == "load")
    actions = {r.action for r in hits}
    if "decline" in actions:
        return "decline", total_load
    if "refer" in actions:
        return "refer", total_load
    if "load" in actions:
        return "approve_adjusted", total_load
    return "auto_approve", 0.0


def underwrite(product: Product, facts: dict, rated_premium: float, rules) -> dict:
    """Run the rules for one applicant. `facts` = cleaned fields + risk_score + risk_band.

    Loads are added together and applied to the rated premium; each load is
    returned as an extra breakdown step so the waterfall shows it.
    """
    hits = [r for r in rules_for(product.code, rules) if matches(r.when, facts)]
    decision, total_load = decide(hits)

    steps, running = [], rated_premium
    for r in hits:
        if r.action == "load":
            change = round(rated_premium * r.load_pct / 100, 2)
            running = round(running + change, 2)
            steps.append({"kind": "underwriting", "code": r.id, "label": r.description,
                          "detail": f"{r.load_pct:+g}% — {r.reason}", "value": None,
                          "multiplier": None, "amount_change": change, "running_total": running})
    if running < product.min_premium:
        steps.append({"kind": "minimum", "code": "min_premium", "label": "Minimum premium",
                      "detail": "Raised to the product minimum", "value": None, "multiplier": None,
                      "amount_change": round(product.min_premium - running, 2),
                      "running_total": float(product.min_premium)})
        running = float(product.min_premium)

    return {
        "decision": decision,
        "total_load_pct": total_load,
        "premium": running,
        "rule_hits": [{"id": r.id, "action": r.action, "load_pct": r.load_pct,
                       "description": r.description, "reason": r.reason} for r in hits],
        "steps": steps,
    }
