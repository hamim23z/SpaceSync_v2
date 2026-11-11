"""GET /catalog?room_type=Living%20Room  ->  CatalogItem[]  (shape from frontend/src/app/lib/types.ts)

Run from the project root:
    pip install fastapi uvicorn pandas
    uvicorn api.catalog_api:app --port 8000
Then set NEXT_PUBLIC_API_URL=http://localhost:8000 in frontend/.env.local.

It reads datasets/catalog.csv. To serve from Supabase instead, replace _load() with a
query on the `catalog` table; the response shape stays the same.
"""
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

CSV = Path(__file__).resolve().parents[1] / "datasets" / "catalog.csv"

# Same list as the frontend's ROOM_TYPES. Bathroom has no priced items yet, so it returns [].
FRONTEND_ROOMS = ["Living Room", "Bedroom", "Kitchen", "Bathroom", "Dining Room"]
ALL_ROOMS = FRONTEND_ROOMS + ["Office", "Kids Room", "Outdoor"]

app = FastAPI(title="SpaceSync catalog API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])


def _load() -> pd.DataFrame:
    return pd.read_csv(CSV)


@app.get("/catalog")
def catalog(room_type: str = Query(..., description="e.g. 'Living Room'")):
    if room_type not in ALL_ROOMS:
        raise HTTPException(status_code=422, detail=f"unknown room_type {room_type!r}; use one of {ALL_ROOMS}")
    df = _load()
    df = df[df["room_type"] == room_type]
    return [
        {
            "item_id": str(r.item_id),  # the frontend types item_id as a string
            "name": r.name,
            "category": r.category,
            "room_type": r.room_type,
            "price_usd": float(r.price_usd),
            "style": r.style_tag,
            "width_cm": float(r.width_cm),
            "depth_cm": float(r.depth_cm),
            "height_cm": float(r.height_cm),
        }
        for r in df.itertuples()
    ]
