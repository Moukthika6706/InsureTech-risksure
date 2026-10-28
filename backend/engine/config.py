"""Load product configs from config/*.yaml.

Any YAML file with `kind: product` is a product — that is the whole
"add a new product" process. rules.yaml and scorecards.yaml are skipped.
"""
import os
from functools import lru_cache
from pathlib import Path

import yaml

from engine.schema import Product

# RISKSURE_CONFIG_DIR lets Docker/Render point at a different folder.
CONFIG_DIR = Path(os.getenv("RISKSURE_CONFIG_DIR",
                            Path(__file__).resolve().parents[2] / "config"))


def read_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:  # utf-8: configs contain ₹
        return yaml.safe_load(fh) or {}


@lru_cache(maxsize=None)
def load_products(config_dir: Path = CONFIG_DIR) -> dict[str, Product]:
    """All products, keyed by code. Validated on load; cached after first call."""
    products = {}
    for path in sorted(Path(config_dir).glob("*.yaml")):
        raw = read_yaml(path)
        if raw.get("kind") != "product":
            continue
        try:
            product = Product.model_validate(raw)
        except ValueError as e:
            raise ValueError(f"Invalid product config {path.name}: {e}") from e
        if product.code in products:
            raise ValueError(f"Duplicate product code '{product.code}' in {path.name}")
        products[product.code] = product
    return products


def get_product(code: str, config_dir: Path = CONFIG_DIR) -> Product:
    products = load_products(config_dir)
    if code not in products:
        raise KeyError(f"Unknown product '{code}'. Available: {sorted(products)}")
    return products[code]
