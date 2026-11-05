# Lesson 1: look at the data before changing it.
# Run from the project folder:  python datasets/explore.py

import pandas as pd

# A DataFrame ("df") is pandas' version of a spreadsheet: rows and named columns.
df = pd.read_csv("datasets/ikea_new_w_prices.csv")

# 1. How big is it?  .shape gives (rows, columns)
print("Rows, columns:", df.shape)

# 2. What columns exist?
print("\nColumns:", df.columns.tolist())

# 3. Peek at a few rows. Only some columns, so it fits on screen.
print("\nFirst 3 rows:")
print(df[["name", "category", "price", "width", "depth", "height"]].head(3))

# 4. What's missing?  .isna() marks blanks as True; .sum() counts them per column.
print("\nMissing values per column:")
print(df[["price", "width", "depth", "height"]].isna().sum())

# 5. Keep only rows that have a price, width AND depth (what the agents need).
usable = df.dropna(subset=["price", "width", "depth"])
print(f"\nUsable rows: {len(usable)} of {len(df)}")

# 6. How many usable items per category?
print("\nUsable items per category:")
print(usable["category"].value_counts())

# 7. Price summary in SAR (Saudi riyals): min, max, average, etc.
print("\nPrice summary (SAR):")
print(usable["price"].describe().round(0))

print(usable[usable["category"] == "Beds"].sort_values("price").head(5))
