from collections import deque
from pathlib import Path
import numpy as np
import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from api.catalog_api import catalog as catalog_endpoint

CSV = Path(__file__).resolve().parents[1] / "datasets" / "catalog.csv"
CELL_CM = 30
TARGET_ITEMS = 5
MAX_PRICE_FRAC = 0.6 #no single piece may cost more than 60% of the budget
UTIL_BAND = (0.25, 0.45)
STYLES = ["modern", "cozy", "minimal", "classic"]

app = FastAPI(title="SpaceSync layout API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["*"])
app.get("/catalog")(catalog_endpoint)


class RoomRequest(BaseModel):
    widthCm: float
    depthCm: float
    roomType: str
    theme: str
    budgetUsd: float

def _clamp(n, lo, hi):
    return max(lo, min(hi, n))

def _reach_frac(grid, door):
    rows, cols = grid.shape
    free = grid == 0
    total = int(free.sum())
    if total == 0:
        return 0.0
    seen = np.zeros_like(free, dtype=bool)
    seen[door] = True
    q, count = deque([door]), 1
    while q:
        r, c = q.popleft()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and free[nr, nc] and not seen[nr, nc]:
                seen[nr, nc] = True
                count += 1
                q.append((nr, nc))
    return count / total

def build_layout(req: RoomRequest, df: pd.DataFrame) -> dict:
    cols = int(_clamp(round(req.widthCm / CELL_CM), 6, 30))
    rows = int(_clamp(round(req.depthCm / CELL_CM), 6, 30))
    grid = np.zeros((rows, cols), dtype=np.int8)
    door = (rows - 1, cols // 2)
    door_cells = {door, (rows - 2, cols // 2)}
    max_cells = max(1, min(rows, cols) // 2)

    items = df[df["room_type"] == req.roomType].copy()
    items["sim"] = np.where(items["style_tag"] == req.theme, 1.0, 0.1 / 0.7)
    items = items[items["price_usd"] <= MAX_PRICE_FRAC * req.budgetUsd]
    items = items.sort_values(["sim", "price_usd"], ascending=[False, True])

    def legal(x, y, w, h):
        if x + w > rows or y + h > cols or grid[x : x + w, y : y + h].any():
            return False
        return not any(x <= r < x + w and y <= c < y + h for r, c in door_cells)

    placed, spend, used = [], 0.0, set()
    for r in items.itertuples():
        if len(placed) >= TARGET_ITEMS:
            break
        if r.category in used or spend + r.price_usd > req.budgetUsd:
            continue
        
        w0 = int(_clamp(round(r.depth_cm / CELL_CM), 1, max_cells))
        h0 = int(_clamp(round(r.width_cm / CELL_CM), 1, max_cells))
        spot = None
        for rotated in (False, True):
            w, h = (h0, w0) if rotated else (w0, h0)
            spots = sorted(
                ((x, y) for x in range(rows - w + 1) for y in range(cols - h + 1)),
                key=lambda p: (min(p[0], p[1], rows - (p[0] + w), cols - (p[1] + h)), p),
            )
            for x, y in spots:
                if legal(x, y, w, h):
                    spot = (x, y, w, h, rotated)
                    break
            if spot:
                break
        if not spot:
            continue
        x, y, w, h, rotated = spot
        grid[x : x + w, y : y + h] = 1
        spend += float(r.price_usd)
        used.add(r.category)
        placed.append(
            dict(
                item_id=str(r.item_id), name=r.name, category=r.category,
                x=x, y=y, w=w, h=h, rotated=rotated,
                price_usd=float(r.price_usd), style=r.style_tag, height_cm=float(r.height_cm),
            )
        )

    util = float(grid.mean())
    walk = _reach_frac(grid, door)
    style_sim = float(np.mean([1.0 if p["style"] == req.theme else 0.1 / 0.7 for p in placed])) if placed else 0.0
    lo, hi = UTIL_BAND
    band = 1.0 if lo <= util <= hi else max(0.0, 1.0 - (lo - util if util < lo else util - hi) / 0.25)
    over = max(0.0, spend - req.budgetUsd) / req.budgetUsd
    return {
        "engine": "rules",
        "room": {"rows": rows, "cols": cols, "cell_cm": CELL_CM},
        "theme": req.theme,
        "budget_usd": req.budgetUsd,
        "spend_usd": spend,
        "items": placed,
        "scores": {
            "layout": round(100 * (0.6 * walk + 0.4 * band)),
            "style": round(100 * style_sim),
            "budget": round(100 * max(0.0, 1.0 - 3.0 * over)),
        },
        "metrics": {
            "utilization": util,
            "walkway_connectivity": walk,
            "style_similarity": style_sim,
            "collision_rate": 0.0,
        },
    }

@app.post("/layout")
def layout(req: RoomRequest):
    return build_layout(req, pd.read_csv(CSV))