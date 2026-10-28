"""Pydantic models describing a product config file (config/<product>.yaml).

Every product YAML is validated against these models when it is loaded, so a
typo in a config file fails loudly at startup instead of mispricing quietly.
"""
from typing import Any, Literal, Optional

from pydantic import BaseModel, field_validator, model_validator


def norm_key(value: Any) -> str:
    """Normalise lookup keys so YAML `1`, `true`, `"1"` and Python 1/True all match."""
    return str(value).strip().lower()


class Option(BaseModel):
    value: Any
    label: str


class FieldSpec(BaseModel):
    """One applicant input. The frontend builds its form from this list."""
    name: str
    label: str
    type: Literal["int", "float", "select", "bool"]
    options: Optional[list[Option]] = None   # for select fields
    min: Optional[float] = None
    max: Optional[float] = None
    default: Any = None
    help: Optional[str] = None
    group: Optional[str] = None              # wizard page this field appears on

    @field_validator("options", mode="before")
    @classmethod
    def plain_options(cls, v):
        # Allow `options: [a, b]` as shorthand for [{value: a, label: a}, ...]
        if v is None:
            return v
        return [o if isinstance(o, dict) else {"value": o, "label": str(o)} for o in v]

    @model_validator(mode="after")
    def select_needs_options(self):
        if self.type == "select" and not self.options:
            raise ValueError(f"select field '{self.name}' needs options")
        return self


class Basis(BaseModel):
    """How a coverage's premium is calculated before rating factors."""
    type: Literal["flat", "percent_of", "per_mille_of"]
    field: Optional[str] = None              # the sum-insured field for percent/per-mille

    @model_validator(mode="after")
    def field_required(self):
        if self.type != "flat" and not self.field:
            raise ValueError(f"basis '{self.type}' needs a field")
        return self


class Coverage(BaseModel):
    code: str
    name: str
    description: str = ""
    mandatory: bool = False
    default: bool = True                     # pre-selected if optional
    basis: Basis
    rate: float                              # flat amount, % or per-mille depending on basis


class Lookup(BaseModel):
    """A rating factor or modifier: maps one applicant field to a multiplier."""
    name: str
    label: str
    field: str
    type: Literal["map", "bands", "percent_discount"]
    values: Optional[dict[Any, float]] = None        # type: map
    bands: Optional[list[tuple[float, float]]] = None  # type: bands, [[upper, multiplier], ...]
    default: Optional[float] = None                  # map fallback for unlisted values

    @model_validator(mode="after")
    def table_present(self):
        if self.type == "map" and not self.values:
            raise ValueError(f"map lookup '{self.name}' needs values")
        if self.type == "bands":
            if not self.bands:
                raise ValueError(f"bands lookup '{self.name}' needs bands")
            uppers = [b[0] for b in self.bands]
            if uppers != sorted(uppers):
                raise ValueError(f"bands for '{self.name}' must be in ascending order")
        return self


class Product(BaseModel):
    kind: Literal["product"]
    code: str
    name: str
    version: str
    description: str = ""
    currency: str = "INR"
    risk: dict[str, Any]                     # how this product is risk-scored (ml_model / scorecard)
    min_premium: float = 0
    fields: list[FieldSpec]
    coverages: list[Coverage]
    rating_factors: list[Lookup] = []
    modifiers: list[Lookup] = []

    @model_validator(mode="after")
    def references_are_valid(self):
        fields = {f.name: f for f in self.fields}
        used = [(c.basis.field, f"coverage '{c.code}'") for c in self.coverages if c.basis.field]
        used += [(l.field, f"lookup '{l.name}'") for l in self.rating_factors + self.modifiers]
        for field, where in used:
            if field not in fields:
                raise ValueError(f"{where} uses unknown field '{field}'")

        # A map lookup on a select field must price every option (catches typos).
        for l in self.rating_factors + self.modifiers:
            f = fields[l.field]
            if l.type == "map" and f.type == "select" and l.default is None:
                keys = {norm_key(k) for k in l.values}
                missing = [o.value for o in f.options if norm_key(o.value) not in keys]
                if missing:
                    raise ValueError(f"lookup '{l.name}' has no multiplier for {missing}")
        return self

    def field(self, name: str) -> FieldSpec:
        return next(f for f in self.fields if f.name == name)
