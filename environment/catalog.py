#loads and validates the SpaceSync furniture catalog that Karthikeya made
import warnings
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "datasets" / "catalog.csv"
STUB_PATH = ROOT / "datasets" / "catalog_stub.csv"
STYLES = ["modern", "cozy", "minimal", "classic"]
SAR_PER_USD = 3.75
REQUIRED = ["item_id", "name", "category", "room_type", "width_cm", "depth_cm", "style_tag"]

def load_catalog(room_type, path=None):
    if path is None:
        if CATALOG_PATH.exists():
            path = CATALOG_PATH
        else:
            path = STUB_PATH
            warnings.warn(
                f"{CATALOG_PATH} not found, using the FAKE stub catalog. "
                "Do not report benchmark numbers from this.",
                stacklevel=2,
            )
    df = pd.read_csv(path)

    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"Catalog {path} is missing columns: {missing}")

    if "price_usd" not in df.columns:
        if "price_sar" not in df.columns:
            raise ValueError("Catalog needs price_usd or price_sar")
        df["price_usd"] = df["price_sar"] / SAR_PER_USD

    df["style_tag"] = df["style_tag"].astype(str).str.strip().str.lower()
    bad_style = ~df["style_tag"].isin(STYLES)
    if bad_style.any():
        warnings.warn(f"Dropping {int(bad_style.sum())} rows with unknown style_tag")
        df = df[~bad_style]

    df = df.dropna(subset=["width_cm", "depth_cm", "price_usd"])
    df = df[(df["width_cm"] > 0) & (df["depth_cm"] > 0) & (df["price_usd"] > 0)]

    rooms = sorted(df["room_type"].unique())
    df = df[df["room_type"] == room_type].reset_index(drop=True)
    if df.empty:
        raise ValueError(f"No priced items for room_type={room_type!r}. Room types in file: {rooms}")
    return df


def split_catalog(df, test_frac=0.2, seed=0):
    #the test train split testing
    rng = np.random.default_rng(seed)
    test_idx = []
    for _, g in df.groupby("category"):
        idx = rng.permutation(g.index.to_numpy())
        n_test = int(round(len(idx) * test_frac))
        if len(idx) >= 2:
            n_test = min(max(n_test, 1), len(idx) - 1)
        else:
            n_test = 0
        test_idx.extend(idx[:n_test].tolist())
    test = df.loc[sorted(test_idx)].reset_index(drop=True)
    train = df.drop(index=test_idx).reset_index(drop=True)
    return train, test