# Lesson 4: "less is more". Pick a small, good set of options for each room.
# Run from the project folder (after assign_rooms.py):  python datasets/curate_catalog.py
# Input:  datasets/catalog.csv          (everything, ~2,500 rows)
# Output: datasets/catalog_curated.csv  (a few options per furniture slot)

import pandas as pd

# A "slot" is one kind of furniture a room needs, e.g. the Bedroom needs a bed,
# a wardrobe and a chest of drawers. Each slot has a regex that matches the
# product types that can fill it. ^ means "starts with", $ means "ends with".
ROOM_SLOTS = {
    "Living Room": {
        "sofa": r"sofa|^corner section",
        "armchair": r"^armchair|chaise longue|rocking",
        "coffee table": r"^coffee table",
        "side table": r"^side table",
        "tv bench": r"^tv bench|^tv storage",
        "bookcase": r"^bookcase|^shelving unit",
    },
    "Bedroom": {
        "bed": r"^bed frame|^day-bed|^bed\b|^loft bed",
        "wardrobe": r"^wardrobe|^open wardrobe",
        "chest of drawers": r"^chest of|^drawer unit",
        "bedside table": r"^bedside table",
        "dressing table": r"^dressing table",
    },
    "Dining Room": {
        "dining table": r"^table$|^extendable table|^drop-leaf table|^gateleg table",
        "dining chair": r"^chair$|^chair with armrests|^folding chair",
        "dining set": r"^table and \d+ chairs",
        "sideboard": r"^sideboard|^buffet|^console table",
        "display cabinet": r"^glass-door cabinet|^cabinet",
    },
    "Office": {
        "desk": r"^desk",
        "office chair": r"^office chair|^swivel chair",
        "bookcase": r"^bookcase|^shelving unit",
    },
    "Kitchen": {
        "bar stool": r"^bar stool",
        "bar table": r"^bar table$",
        "kitchen island": r"^kitchen island|^kitchen trolley|^trolley",
    },
    "Kids Room": {
        "bed": r"^cot|bed",
        "chair": r"^children's (?:chair|desk chair|armchair)|^junior chair",
        "desk": r"^desk|^children's table",
        "storage": r"^storage combination|^wardrobe|^wall storage",
    },
    "Outdoor": {
        "table": r"^table",
        "chair": r"^chair|^armchair",
        "sofa": r"sofa",
    },
}

PER_TIER = 2  # options per price tier -> up to 6 per slot (2 budget, 2 mid, 2 premium)


def pick_options(items):
    """From all items that fit one slot, keep a few spread across prices."""
    # Not enough items to split into tiers? Just keep them all.
    if len(items) <= PER_TIER * 3:
        return items.assign(tier="all")

    # pd.qcut splits prices into 3 equal-sized groups: cheapest third,
    # middle third and most expensive third.
    items = items.assign(
        tier=pd.qcut(items["price_usd"], 3, labels=["budget", "mid", "premium"], duplicates="drop")
    )
    picks = []
    for tier, group in items.groupby("tier", observed=True):
        # In each tier, take the items whose price is closest to that tier's
        # typical (median) price, so we skip odd outliers.
        distance = (group["price_usd"] - group["price_usd"].median()).abs()
        picks.append(group.loc[distance.nsmallest(PER_TIER).index])
    return pd.concat(picks)


df = pd.read_csv("datasets/catalog.csv")

# The same product in different colors shows up as separate rows
# (same name, same product type). Keep only the cheapest version of each.
df = df.sort_values("price_usd").drop_duplicates(subset=["room", "name", "product_type"])

curated = []
for room, slots in ROOM_SLOTS.items():
    room_items = df[df["room"] == room]
    for slot, pattern in slots.items():
        fits = room_items[room_items["product_type"].str.contains(pattern, case=False, regex=True)]
        if len(fits) == 0:
            print(f"WARNING: no items for {room} / {slot}")
            continue
        picks = pick_options(fits).assign(slot=slot)
        curated.append(picks)

result = pd.concat(curated)
result = result[["room", "slot", "tier"] + [c for c in result.columns if c not in ("room", "slot", "tier")]]
result = result.sort_values(["room", "slot", "price_usd"])
result.to_csv("datasets/catalog_curated.csv", index=False)

print(f"Curated {len(result)} rows (from {len(df)}) saved to datasets/catalog_curated.csv\n")
summary = result.groupby(["room", "slot"]).agg(
    options=("item_id", "count"),
    cheapest=("price_usd", "min"),
    priciest=("price_usd", "max"),
)
print(summary.to_string())
