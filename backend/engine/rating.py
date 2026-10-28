"""Generic rating engine: works for any product defined in config/.

premium = sum(coverage base premiums) x rating factors x modifiers,
floored at the product's minimum premium. Every step is recorded so the UI
can show exactly how the price was built (the waterfall chart).

Nothing here knows about cars, homes or shops — all numbers come from YAML.
"""
from typing import Any, Optional

from engine.schema import Coverage, FieldSpec, Lookup, Product, norm_key


class ApplicantError(ValueError):
    """Applicant data doesn't match the product's fields. `errors` lists every problem."""

    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


# ------------------------------------------------------------ validation

def _clean_value(f: FieldSpec, value: Any) -> Any:
    """Convert one raw value to the field's type, or raise ValueError."""
    if f.type == "bool":
        key = norm_key(value)
        if key in ("true", "1", "yes"):
            return True
        if key in ("false", "0", "no"):
            return False
        raise ValueError("must be true or false")
    if f.type == "select":
        for o in f.options:
            if norm_key(o.value) == norm_key(value):
                return o.value
        raise ValueError(f"must be one of {[o.value for o in f.options]}")
    # int / float
    if isinstance(value, bool):
        raise ValueError("must be a number")
    number = float(value)
    if f.type == "int":
        if number != int(number):
            raise ValueError("must be a whole number")
        number = int(number)
    if f.min is not None and number < f.min:
        raise ValueError(f"must be at least {f.min:g}")
    if f.max is not None and number > f.max:
        raise ValueError(f"must be at most {f.max:g}")
    return number


def validate_applicant(product: Product, applicant: dict) -> dict:
    """Return the applicant's fields cleaned to the right types. Extra keys are ignored."""
    clean, errors = {}, []
    for f in product.fields:
        if applicant.get(f.name) is None:
            errors.append(f"{f.name}: required")
            continue
        try:
            clean[f.name] = _clean_value(f, applicant[f.name])
        except (ValueError, TypeError) as e:
            errors.append(f"{f.name}: {e}")
    if errors:
        raise ApplicantError(errors)
    return clean


def choose_coverages(product: Product, selected: Optional[list[str]] = None) -> list[Coverage]:
    """Mandatory coverages plus the selected optional ones (or the defaults if none given)."""
    if selected is None:
        return [c for c in product.coverages if c.mandatory or c.default]
    known = {c.code for c in product.coverages}
    unknown = [s for s in selected if s not in known]
    if unknown:
        raise ApplicantError([f"unknown coverage(s): {unknown}"])
    return [c for c in product.coverages if c.mandatory or c.code in selected]


# --------------------------------------------------------------- lookups

def lookup(table: Lookup, value: Any) -> float:
    """Multiplier for one rating factor / modifier."""
    if table.type == "map":
        for k, m in table.values.items():
            if norm_key(k) == norm_key(value):
                return m
        if table.default is not None:
            return table.default
        raise ApplicantError([f"{table.field}: no '{table.name}' multiplier for {value!r}"])
    if table.type == "bands":
        for upper, m in table.bands:   # first band whose upper bound covers the value
            if value <= upper:
                return m
        return table.bands[-1][1]      # above the last band: use the top band
    if table.type == "percent_discount":
        return 1 - float(value) / 100
    raise ValueError(f"unknown lookup type {table.type}")


def coverage_premium(cov: Coverage, data: dict) -> float:
    if cov.basis.type == "flat":
        return cov.rate
    exposure = data[cov.basis.field]
    if cov.basis.type == "percent_of":
        return exposure * cov.rate / 100
    return exposure * cov.rate / 1000  # per_mille_of


# ------------------------------------------------------------ formatting

def inr(amount: float) -> str:
    """Indian digit grouping: 1234567 -> ₹12,34,567."""
    s = str(round(amount))
    if len(s) <= 3:
        return f"₹{s}"
    head, tail = s[:-3], s[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    return "₹" + ",".join([head] + groups + [tail])


def _display(f: FieldSpec, value: Any) -> str:
    if f.type == "bool":
        return "Yes" if value else "No"
    if f.type == "select":
        return next(o.label for o in f.options if o.value == value)
    return f"{value:,}" if isinstance(value, int) else str(value)


def _basis_text(product: Product, cov: Coverage, data: dict) -> str:
    if cov.basis.type == "flat":
        return f"Flat {inr(cov.rate)}"
    label = product.field(cov.basis.field).label
    amount = inr(data[cov.basis.field])
    if cov.basis.type == "percent_of":
        return f"{cov.rate:g}% of {label} ({amount})"
    return f"₹{cov.rate:g} per ₹1,000 of {label} ({amount})"   # keep decimals: ₹1.139, not ₹1"


# ------------------------------------------------------------------ rate

def rate(product: Product, applicant: dict, coverages: Optional[list[str]] = None) -> dict:
    """Price one applicant. Returns the premium and a step-by-step breakdown.

    Each step has amount_change and running_total; amounts are rounded to
    paise at each step so the waterfall adds up exactly to the premium.
    """
    data = validate_applicant(product, applicant)
    chosen = choose_coverages(product, coverages)
    steps: list[dict] = []
    exact = 0.0     # unrounded running total used for the maths
    shown = 0.0     # rounded running total shown in the breakdown

    def record(kind, code, label, detail, multiplier=None, value=None):
        nonlocal shown
        new_shown = round(exact, 2)
        steps.append({
            "step": len(steps) + 1, "kind": kind, "code": code, "label": label,
            "detail": detail, "value": value, "multiplier": multiplier,
            "amount_change": round(new_shown - shown, 2), "running_total": new_shown,
        })
        shown = new_shown

    cov_lines = []
    for cov in chosen:
        premium = coverage_premium(cov, data)
        exact += premium
        cov_lines.append({"code": cov.code, "name": cov.name, "premium": round(premium, 2)})
        record("coverage", cov.code, cov.name, _basis_text(product, cov, data))
    base_premium = shown

    for kind, tables in (("factor", product.rating_factors), ("modifier", product.modifiers)):
        for t in tables:
            value = data[t.field]
            m = lookup(t, value)
            exact *= m
            detail = f"{product.field(t.field).label}: {_display(product.field(t.field), value)}"
            record(kind, t.name, t.label, detail, multiplier=m, value=value)

    if exact < product.min_premium:
        exact = float(product.min_premium)
        record("minimum", "min_premium", "Minimum premium",
               f"Raised to the product minimum of {inr(product.min_premium)}")

    return {
        "product": product.code,
        "currency": product.currency,
        "coverages": cov_lines,
        "base_premium": base_premium,
        "premium": shown,
        "steps": steps,
    }
