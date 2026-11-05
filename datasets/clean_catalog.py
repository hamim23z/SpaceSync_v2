# Lesson 2: clean the priced IKEA dataset into one table the agents can trust.
# Run from the project folder:  python datasets/clean_catalog.py
# Input:  datasets/ikea_new_w_prices.csv
# Output: datasets/catalog_clean.csv

import pandas as pd

SAR_PER_USD = 3.75  # the Saudi riyal is pegged to the dollar at 3.75

# Words that mean "this is a part or accessory, not a piece of furniture".
# We check them against the product type (the description text before the first comma).
# Rule A: the product type STARTS with one of these ("Handle", "Cover for 3-seat sofa").
PART_WORDS = [
    "handle", "knob", "leg", "door", "drawer front", "drawer frame", "shelf",
    "table top", "desk top", "top", "cover", "cushion", "pad", "headboard",
    "slatted bed base", "storage box", "frame for", "underframe", "castor",
    "hinge", "rail", "plinth", "panel", "insert", "divider for", "box",
    "basket", "hook", "lock", "connecting fitting", "wall upright",
    "inner cushion", "storage bag", "padded seat cover", "laptop support",
]
# Rule B: the product type ENDS with one of these ("Glass door", "Chair cushion"),
# unless it says "with"/"w" ("Wardrobe with 2 doors" is a wardrobe, keep it).
PART_ENDINGS = ["door", "cushion", "pad", "cover", "top", "panel"]

df = pd.read_csv("datasets/ikea_new_w_prices.csv")
print("Start:", len(df), "rows")

# --- Step 1: drop columns we don't need ------------------------------------
# "Unnamed: 0" is a leftover row number; the others aren't useful to the agents.
df = df.drop(columns=["Unnamed: 0", "old_price", "sellable_online", "designer"])

# --- Step 2: remove duplicate products -------------------------------------
# The same item_id can appear under two categories (e.g. a chair listed under
# "Chairs" and "Bar furniture"). Keep the first copy of each product.
df = df.drop_duplicates(subset="item_id")
print("After removing duplicates:", len(df))

# --- Step 3: tidy the description text -------------------------------------
# Descriptions have lots of extra spaces: "Bar table,          51x51 cm".
# .split() breaks on any run of spaces, " ".join() glues back with one space.
df["description"] = df["short_description"].fillna("").apply(lambda s: " ".join(s.split()))
df = df.drop(columns=["short_description"])

# The product type is the text before the first comma: "Bar table".
df["product_type"] = df["description"].str.split(",").str[0].str.strip()

# --- Step 4: recover missing sizes from the description --------------------
# A regex (regular expression) is a pattern for finding text.
#   (\d+)      one or more digits, and the ( ) "captures" them
#   x          a literal letter x
#   (?:x(\d+))? an optional third number
# So "51x51 cm" gives 51 and 51; "25x51x73 cm" gives 25, 51, 73.
sizes = df["description"].str.extract(r"(\d+)x(\d+)(?:x(\d+))? cm").astype(float)

filled_width = df["width"].isna() & sizes[0].notna()
filled_depth = df["depth"].isna() & sizes[1].notna()
df.loc[filled_width, "width"] = sizes[0]  # only fills blanks, never overwrites
df.loc[filled_depth, "depth"] = sizes[1]
print(f"Recovered {filled_width.sum()} widths and {filled_depth.sum()} depths from descriptions")

# Remember which sizes we filled in, so nobody mistakes them for measured values.
df["size_from_description"] = filled_width | filled_depth

# --- Step 5: keep only rows with a price, width and depth ------------------
df = df.dropna(subset=["price", "width", "depth"])
print("After dropping rows without price/width/depth:", len(df))

# --- Step 6: remove parts and accessories ----------------------------------
# Build one regex like ^(handle|knob|leg|...)\b  meaning "starts with one of these words".
# case=False ignores capital letters.
starts_pattern = r"^(?:" + "|".join(PART_WORDS) + r")\b"
ends_pattern = r"\b(?:" + "|".join(PART_ENDINGS) + r")s?$"  # s? allows plurals
starts_with_part = df["product_type"].str.contains(starts_pattern, case=False, regex=True)
ends_with_part = df["product_type"].str.contains(ends_pattern, case=False, regex=True)
says_with = df["product_type"].str.contains(r"\b(?:with|w)\b", case=False, regex=True)
is_part = starts_with_part | (ends_with_part & ~says_with)  # | means "or", & means "and"
print("Removing", is_part.sum(), "parts/accessories")
df = df[~is_part]  # ~ means "not", so keep the rows that are NOT parts

# --- Step 7: convert price to US dollars -----------------------------------
df = df.rename(columns={"price": "price_sar"})
df["price_usd"] = (df["price_sar"] / SAR_PER_USD).round(2)

# --- Save -------------------------------------------------------------------
columns = [
    "item_id", "name", "category", "product_type", "description",
    "price_usd", "price_sar", "width", "depth", "height",
    "size_from_description", "other_colors", "link",
]
df = df[columns].rename(columns={"width": "width_cm", "depth": "depth_cm", "height": "height_cm"})
df.to_csv("datasets/catalog_clean.csv", index=False)

print("\nFinal:", len(df), "rows saved to datasets/catalog_clean.csv")
print("\nItems per category:")
print(df["category"].value_counts())
