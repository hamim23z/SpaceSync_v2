# Final step: turn the curated picks into the one clean catalog the env, API and website use.
# Run from the project folder:  python datasets/build_final_catalog.py
# Inputs: datasets/catalog_curated.csv  (output of curate_catalog.py)
#         datasets/catalog_full.csv     (output of assign_rooms.py, used only for median heights)
# Output: datasets/catalog.csv
#
# Pipeline file names:  assign_rooms.py -> catalog_full.csv -> curate_catalog.py
#                       -> catalog_curated.csv -> build_final_catalog.py -> catalog.csv

import re
import unicodedata

import pandas as pd

from catalog import STYLES

df = pd.read_csv("datasets/catalog_curated.csv")
full = pd.read_csv("datasets/catalog_full.csv")
df["size_note"] = ""


def described_dims(text):
    """'Table, 120x60 cm' -> (120, 60). For '130/190x80' uses the larger (extended) 190."""
    m = re.search(r"(\d+)(?:/(\d+))?x(\d+)(?:x(\d+))? cm", str(text))
    if not m:
        return None
    first = float(m.group(2) or m.group(1))
    return first, float(m.group(3))


# --- Fix 1: footprint bug --------------------------------------------------
# The old cleaning step copied the description's 2nd number into depth, but the raw
# width column already held that same number, so width == depth == the SHORT side.
# If that matches the description, the first number is the real long side.
fixed = 0
for i, r in df.iterrows():
    d = described_dims(r["description"])
    if d is None:
        continue
    long_side, short_side = d
    if r["width_cm"] == r["depth_cm"] == short_side and long_side > short_side:
        df.loc[i, "width_cm"] = long_side
        df.loc[i, "size_note"] = "footprint fixed from description"
        fixed += 1
print("Footprints fixed:", fixed)

# Dining sets: the size in the description is the table only, chairs are extra.
mask = df["slot"] == "dining set"
df.loc[mask, "size_note"] = df.loc[mask, "size_note"].apply(
    lambda s: (s + "; " if s else "") + "table size only"
)

# --- Fix 2: drop rows whose stored size clearly belongs to something else --
bad = (
    ((df["slot"] == "bed") & (df["depth_cm"] < 100) & df["description"].str.contains("200 cm"))
    | ((df["slot"] == "bedside table") & (df["height_cm"] < 20))
)
print("Dropping implausible rows:", df.loc[bad, ["room", "name", "description"]].values.tolist())
df = df[~bad]

# --- Fix 3: fill missing heights with medians, and flag them ---------------
# Median of the same product type (needs 3+ real heights), else of the category.
full = full[full["height_cm"] >= 20]
by_type = full.groupby("product_type")["height_cm"].agg(["median", "count"])
by_cat = full.groupby("category")["height_cm"].median()


def median_height(row):
    pt = row["product_type"]
    if pt in by_type.index and by_type.loc[pt, "count"] >= 3:
        return by_type.loc[pt, "median"]
    return by_cat.get(row["category"])


df["height_imputed"] = df["height_cm"].isna()
df.loc[df["height_imputed"], "height_cm"] = df[df["height_imputed"]].apply(median_height, axis=1)
print("Heights filled with medians:", int(df["height_imputed"].sum()),
      "| still missing:", int(df["height_cm"].isna().sum()))

# --- Style tag (a HEURISTIC, not ground truth) -----------------------------
# IKEA's data has no style. We look only at the colour/material words in the product
# link (e.g. ".../trysil-bed-frame-white-light-grey-..."), after removing the product's
# own name and type words. Each style has a keyword list; the style with the most hits
# wins (ties go to the earlier style in STYLE_KEYWORDS). No hits -> "minimal", marked
# style_source="default" so you can see which tags are real signals and which are filler.
STYLE_KEYWORDS = {
    "classic": {"stained", "stain", "antique", "veneer", "oak", "walnut"},
    "cozy": {"brown", "beige", "rattan", "pink", "yellow", "red", "green", "blue", "pine"},
    "modern": {"black", "anthracite", "grey", "chrome", "glass", "metal", "steel",
               "stainless", "galvanised", "gold", "golden", "plated", "concrete"},
    "minimal": {"white", "ash", "birch", "beech"},
}
assert set(STYLE_KEYWORDS) == set(STYLES)


def fold(s):
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()


def words(s):
    return set(re.findall(r"[a-z]+", fold(s)))


def tag_style(row):
    slug = row["link"].split("/p/")[1].rsplit("-", 1)[0] if "/p/" in row["link"] else ""
    own = words(row["name"]) | words(row["product_type"]) | words(row["description"])
    left = [t for t in re.findall(r"[a-z]+", fold(slug)) if t not in own]
    scores = {s: sum(t in kw for t in left) for s, kw in STYLE_KEYWORDS.items()}
    best = max(scores.values())
    if best == 0:
        return "minimal", "default"
    return next(s for s in STYLE_KEYWORDS if scores[s] == best), "keywords"


df[["style_tag", "style_source"]] = df.apply(lambda r: pd.Series(tag_style(r)), axis=1)

# --- Key: the same item can appear in two rooms (bookcases) ----------------
assert not df.duplicated(["room", "item_id"]).any()

# --- Tidy for the env, API and website -------------------------------------
df["other_colors"] = df["other_colors"].eq("Yes")  # True/False instead of Yes/No
df = df.rename(columns={"room": "room_type"})
columns = [
    "room_type", "slot", "tier", "item_id", "name", "category", "product_type", "description",
    "price_usd", "price_sar", "width_cm", "depth_cm", "height_cm", "height_imputed",
    "style_tag", "style_source", "size_from_description", "size_note", "other_colors", "link",
]
df = df[columns].sort_values(["room_type", "slot", "price_usd"])
df.to_csv("datasets/catalog.csv", index=False)

print(f"\nSaved {len(df)} rows to datasets/catalog.csv")
print(df.groupby("room_type").agg(items=("item_id", "count"), slots=("slot", "nunique")).to_string())
print("\nStyle tags:", df["style_tag"].value_counts().to_dict())
print("Style source:", df["style_source"].value_counts().to_dict())
