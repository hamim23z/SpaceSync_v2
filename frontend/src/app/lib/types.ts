/**
 * Shared types. The shapes here match what the Python env produces, so that
 * swapping the mock data for the real API later is just a URL change.
 */

export const STYLES = ["modern", "cozy", "minimal", "classic"] as const;
export type StyleTag = (typeof STYLES)[number];

export const ROOM_TYPES = ["Living Room", "Bedroom", "Kitchen", "Bathroom", "Dining Room"] as const;
export type RoomType = (typeof ROOM_TYPES)[number];

/** What the user asks for on the "Enter room dimensions" screen. Sizes are in cm. */
export interface RoomRequest {
  widthCm: number; // along the X axis (the grid's columns)
  depthCm: number; // along the Z axis (the grid's rows)
  roomType: RoomType;
  theme: StyleTag;
  budgetUsd: number;
}

/**
 * One placed piece. Same fields as `env.get_layout()` in the Python env,
 * plus an optional height_cm (add it to the env's layout_log so the 3D boxes
 * get the right height; until then the frontend falls back to 80 cm).
 *
 * Grid convention (identical to the env):
 *   x = row index    (runs along the room's DEPTH)
 *   y = column index (runs along the room's WIDTH)
 *   w = cells covered along rows, h = cells covered along columns
 *   (rotation is already applied: `rotated` just records that it was)
 */
export interface PlacedItem {
  item_id: string;
  name: string;
  category: string;
  x: number;
  y: number;
  w: number;
  h: number;
  rotated: boolean;
  price_usd: number;
  style: StyleTag;
  height_cm?: number;
}

export interface AgentScores {
  layout: number;
  style: number;
  budget: number;
}

export interface LayoutMetrics {
  utilization: number;
  walkway_connectivity: number;
  style_similarity: number;
  collision_rate: number; // illegal placements
}

export interface LayoutResult {
  /** "mock" until the real agents are connected. The UI shows a banner for it. */
  source: "mock" | "api";
  room: { rows: number; cols: number; cell_cm: number };
  theme: StyleTag;
  budget_usd: number;
  spend_usd: number;
  items: PlacedItem[];
  scores: AgentScores;
  metrics: LayoutMetrics;
}

export interface CatalogItem {
  item_id: string;
  name: string;
  category: string;
  room_type: RoomType;
  price_usd: number;
  style: StyleTag;
  width_cm: number;
  depth_cm: number;
  height_cm: number;
}