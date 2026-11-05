# Lesson 3: decide which room(s) each item belongs in.
# Run from the project folder (after clean_catalog.py):  python datasets/assign_rooms.py
# Input:  datasets/catalog_clean.csv
# Output: datasets/catalog.csv  (one row per item per room)

import re
import pandas as pd

# Default rooms for each IKEA category. A list, because one category can fit
# several rooms (a bookcase works in a living room or an office).
CATEGORY_ROOMS = {
    "Sofas & armchairs": ["Living Room"],
    "TV & media furniture": ["Living Room"],
    "Room dividers": ["Living Room"],
    "Bookcases & shelving units": ["Living Room", "Office"],
    "Cabinets & cupboards": ["Living Room", "Dining Room"],
    "Sideboards, buffets & console tables": ["Dining Room", "Living Room"],
    "Beds": ["Bedroom"],
    "Wardrobes": ["Bedroom"],
    "Chests of drawers & drawer units": ["Bedroom"],
    "Tables & desks": ["Dining Room"],
    "Chairs": ["Dining Room"],
    "Café furniture": ["Dining Room", "Kitchen"],
    "Bar furniture": ["Kitchen"],
    "Trolleys": ["Kitchen"],
    "Children's furniture": ["Kids Room"],
    "Nursery furniture": ["Kids Room"],
    "Outdoor furniture": ["Outdoor"],
}

# Some categories are too broad. "Tables & desks" holds desks (Office),
# coffee tables (Living Room) and bedside tables (Bedroom). So we look at the
# product type first. Rules are checked top to bottom; the first match wins.
PRODUCT_TYPE_RULES = [
    (r"children|junior|cot\b|highchair|baby", ["Kids Room"]),
    (r"desk|office chair|swivel chair|conference", ["Office"]),
    (r"bedside|dressing table", ["Bedroom"]),
    (r"coffee table|side table|armchair|chaise longue|rocking", ["Living Room"]),
    (r"table and \d+ chairs|dining|extendable table|drop-leaf|gateleg", ["Dining Room"]),
    (r"kitchen", ["Kitchen"]),
]

# Outdoor items stay outdoors even if they're called "Armchair".
KEEP_CATEGORY_ROOMS = {"Outdoor furniture", "Children's furniture", "Nursery furniture"}


def pick_rooms(row):
    """Return the list of rooms for one item (one row of the table)."""
    if row["category"] not in KEEP_CATEGORY_ROOMS:
        for pattern, rooms in PRODUCT_TYPE_RULES:
            if re.search(pattern, row["product_type"], flags=re.IGNORECASE):
                return rooms
    # No rule matched: fall back to the category's default rooms.
    return CATEGORY_ROOMS.get(row["category"], [])


df = pd.read_csv("datasets/catalog_clean.csv")

# .apply(..., axis=1) runs pick_rooms once for every row and collects the answers.
df["room"] = df.apply(pick_rooms, axis=1)

# Safety check: did any category get no room? (e.g. a typo in CATEGORY_ROOMS)
unassigned = df[df["room"].str.len() == 0]
if len(unassigned) > 0:
    print("WARNING: no room for these categories:", unassigned["category"].unique().tolist())

# .explode() turns one row with ["Living Room", "Office"] into two rows,
# one per room. That makes "give me everything for the Office" a simple filter.
df = df.explode("room").dropna(subset=["room"])

# Put the room column first, it's what everyone will filter by.
df = df[["room"] + [c for c in df.columns if c != "room"]]
df.to_csv("datasets/catalog.csv", index=False)

print(f"Saved {len(df)} rows ({df['item_id'].nunique()} unique items) to datasets/catalog.csv")
print("\nItems per room:")
print(df["room"].value_counts())
