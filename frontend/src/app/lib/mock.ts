import { CatalogItem, LayoutResult, PlacedItem, RoomRequest, RoomType, StyleTag } from "./types";

/**
 * MOCK DATA. This stands in for the real catalog and the trained agents so the
 * website can be built before the backend exists. Nothing here comes from the
 * trained models. The room page shows a "demo data" banner while source is "mock".
 */

const CELL_CM = 30;

let n = 0;
const item = (
  room_type: RoomType,
  category: string,
  name: string,
  style: StyleTag,
  price_usd: number,
  width_cm: number,
  depth_cm: number,
  height_cm: number
): CatalogItem => ({ item_id: `MOCK${String(++n).padStart(3, "0")}`, room_type, category, name, style, price_usd, width_cm, depth_cm, height_cm });

export const MOCK_CATALOG: CatalogItem[] = [
  // Living Room
  item("Living Room", "Sofa", "Modern 3-seat sofa", "modern", 649, 210, 90, 80),
  item("Living Room", "Sofa", "Cozy 2-seat loveseat", "cozy", 429, 150, 88, 78),
  item("Living Room", "Sofa", "Classic roll-arm sofa", "classic", 780, 205, 92, 85),
  item("Living Room", "Armchair", "Minimal lounge chair", "minimal", 190, 70, 78, 82),
  item("Living Room", "Armchair", "Cozy wingback chair", "cozy", 260, 82, 85, 98),
  item("Living Room", "Coffee table", "Modern coffee table", "modern", 120, 100, 55, 42),
  item("Living Room", "Coffee table", "Minimal round table", "minimal", 85, 70, 70, 40),
  item("Living Room", "TV unit", "Modern TV unit", "modern", 210, 160, 40, 50),
  item("Living Room", "Bookcase", "Classic bookcase", "classic", 150, 80, 30, 180),
  item("Living Room", "Side table", "Cozy side table", "cozy", 45, 45, 45, 55),
  // Bedroom
  item("Bedroom", "Bed", "Modern queen bed", "modern", 520, 160, 205, 90),
  item("Bedroom", "Bed", "Cozy upholstered bed", "cozy", 610, 165, 210, 110),
  item("Bedroom", "Wardrobe", "Minimal wardrobe", "minimal", 340, 150, 58, 210),
  item("Bedroom", "Chest of drawers", "Classic dresser", "classic", 260, 100, 48, 95),
  item("Bedroom", "Bedside table", "Modern nightstand", "modern", 70, 45, 38, 55),
  item("Bedroom", "Desk", "Minimal desk", "minimal", 160, 120, 60, 74),
  // Kitchen
  item("Kitchen", "Kitchen island", "Modern kitchen island", "modern", 420, 120, 70, 90),
  item("Kitchen", "Trolley", "Cozy rolling trolley", "cozy", 90, 50, 40, 85),
  item("Kitchen", "Storage cabinet", "Classic pantry cabinet", "classic", 230, 80, 40, 180),
  item("Kitchen", "Bar table", "Minimal bar table", "minimal", 150, 100, 60, 102),
  // Bathroom
  item("Bathroom", "Vanity unit", "Modern vanity", "modern", 310, 80, 47, 85),
  item("Bathroom", "Storage tower", "Minimal storage tower", "minimal", 120, 35, 35, 170),
  item("Bathroom", "Wall cabinet", "Classic wall cabinet", "classic", 95, 60, 16, 70),
  // Dining Room
  item("Dining Room", "Dining table", "Modern dining table", "modern", 360, 180, 90, 75),
  item("Dining Room", "Dining chair", "Cozy dining chair", "cozy", 55, 45, 50, 90),
  item("Dining Room", "Sideboard", "Classic sideboard", "classic", 280, 150, 42, 85),
  item("Dining Room", "Bench", "Minimal bench", "minimal", 110, 120, 35, 47),
];

export const mockCatalog = (roomType: RoomType) => MOCK_CATALOG.filter((i) => i.room_type === roomType);
const cells = (cm: number) => Math.max(1, Math.min(7, Math.round(cm / CELL_CM)));

export function buildMockLayout(req: RoomRequest): LayoutResult {
  const cols = Math.max(6, Math.min(30, Math.round(req.widthCm / CELL_CM)));
  const rows = Math.max(6, Math.min(30, Math.round(req.depthCm / CELL_CM)));
  const grid: boolean[][] = Array.from({ length: rows }, () => Array<boolean>(cols).fill(false));
  const doorCol = Math.floor(cols / 2);
  const reserved = new Set([`${rows - 1},${doorCol}`, `${rows - 2},${doorCol}`]);

  const fits = (x: number, y: number, w: number, h: number) => {
    if (x + w > rows || y + h > cols) return false;
    for (let i = x; i < x + w; i++)
      for (let j = y; j < y + h; j++) if (grid[i][j] || reserved.has(`${i},${j}`)) return false;
    return true;
  };

  const candidates = mockCatalog(req.roomType)
    .slice()
    .sort((a, b) => Number(b.style === req.theme) - Number(a.style === req.theme) || b.width_cm * b.depth_cm - a.width_cm * a.depth_cm);

  const placed: PlacedItem[] = [];
  let spend = 0;
  const usedCategories = new Set<string>();
  const maxItems = 5;
  const totalCells = rows * cols;

  for (const c of candidates) {
    if (placed.length >= maxItems) break;
    if (usedCategories.has(c.category)) continue;
    if (spend + c.price_usd > req.budgetUsd) continue;
    const w0 = cells(c.depth_cm);
    const h0 = cells(c.width_cm);
    let spot: { x: number; y: number; w: number; h: number; rotated: boolean } | null = null;
    for (const rotated of [false, true]) {
      const [w, h] = rotated ? [h0, w0] : [w0, h0];
      const order: [number, number][] = [];
      for (let x = 0; x < rows; x++) for (let y = 0; y < cols; y++) order.push([x, y]);
      order.sort(([ax, ay], [bx, by]) => wallDist(ax, ay, rows, cols, w, h) - wallDist(bx, by, rows, cols, w, h));
      for (const [x, y] of order) {
        if (fits(x, y, w, h)) {
          spot = { x, y, w, h, rotated };
          break;
        }
      }
      if (spot) break;
    }
    if (!spot) continue;
    for (let i = spot.x; i < spot.x + spot.w; i++) for (let j = spot.y; j < spot.y + spot.h; j++) grid[i][j] = true;
    usedCategories.add(c.category);
    spend += c.price_usd;
    placed.push({
      item_id: c.item_id,
      name: c.name,
      category: c.category,
      ...spot,
      price_usd: c.price_usd,
      style: c.style,
      height_cm: c.height_cm,
    });
  }

  const covered = placed.reduce((s, p) => s + p.w * p.h, 0);
  const utilization = covered / totalCells;
  const styleSim = placed.length ? placed.reduce((s, p) => s + (p.style === req.theme ? 1 : 0.15), 0) / placed.length : 0;
  const underBudget = spend <= req.budgetUsd;
  const inBand = utilization >= 0.25 && utilization <= 0.45;

  return {
    source: "mock",
    room: { rows, cols, cell_cm: CELL_CM },
    theme: req.theme,
    budget_usd: req.budgetUsd,
    spend_usd: spend,
    items: placed,
    scores: {
      layout: Math.round(100 * Math.min(1, 0.55 + (inBand ? 0.4 : 0.15) + 0.05)),
      style: Math.round(100 * styleSim),
      budget: Math.round(100 * (underBudget ? 0.6 + 0.4 * Math.min(1, spend / req.budgetUsd) : 0.2)),
    },
    metrics: { utilization, walkway_connectivity: 1, style_similarity: styleSim, collision_rate: 0 },
  };
}

function wallDist(x: number, y: number, rows: number, cols: number, w: number, h: number) {
  return Math.min(x, y, rows - (x + w), cols - (y + h));
}