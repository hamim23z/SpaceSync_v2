export const STYLES = ["modern", "cozy", "minimal", "classic"] as const;
export type StyleTag = (typeof STYLES)[number];
export const ROOM_TYPES = ["Living Room", "Bedroom", "Kitchen", "Bathroom", "Dining Room"] as const;
export type RoomType = (typeof ROOM_TYPES)[number];

export interface RoomRequest {
  widthCm: number;
  depthCm: number;
  roomType: RoomType;
  theme: StyleTag;
  budgetUsd: number;
}

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
  collision_rate: number; //illegal placements
}

export interface LayoutResult {
  source: "mock" | "api";
  engine?: "rules" | "agents";
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