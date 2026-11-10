"""Catalog loader shared by the env, the API and the build script.

spacesync_env.py does `from catalog import STYLES`, so this file must be importable
from the environment/ folder (put it there, or add datasets/ to PYTHONPATH).
"""
from pathlib import Path

import pandas as pd

STYLES = ["modern", "cozy", "minimal", "classic"]  # same order as frontend/src/app/lib/types.ts

CATALOG_PATH = Path(__file__).resolve().parent / "catalog.csv"

# Columns SpaceSyncEnv reads: item_id, name, category, width_cm, depth_cm, price_usd, style_tag
REQUIRED = ["item_id", "name", "category", "room_type", "price_usd",
            "width_cm", "depth_cm", "height_cm", "style_tag"]


def load_catalog(room_type=None, path=CATALOG_PATH):
    """Return the catalog, optionally only the items for one room type, as a DataFrame."""
    df = pd.read_csv(path)
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"catalog is missing columns: {missing}")
    bad = set(df["style_tag"]) - set(STYLES)
    if bad:
        raise ValueError(f"unknown style tags: {bad}")
    if room_type is not None:
        df = df[df["room_type"] == room_type]
        if df.empty:
            raise ValueError(f"no catalog items for room type {room_type!r}")
    return df.reset_index(drop=True)
