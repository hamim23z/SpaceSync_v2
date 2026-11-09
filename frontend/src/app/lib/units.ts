import { RoomRequest, RoomType, ROOM_TYPES, STYLES, StyleTag } from "./types";

export const CM_PER_FT = 30.48;
export const CM_PER_M = 100;
export const MIN_ROOM_CM = 180;
export const MAX_ROOM_CM = 900;

export type Unit = "ft" | "m";

export const toCm = (value: number, unit: Unit) => value * (unit === "ft" ? CM_PER_FT : CM_PER_M);
export const fromCm = (cm: number, unit: Unit) => cm / (unit === "ft" ? CM_PER_FT : CM_PER_M);


export function formatSize(widthCm: number, depthCm: number, unit: Unit = "ft") {
  const f = (cm: number) => String(Math.round(fromCm(cm, unit) * 10) / 10);
  return `${f(widthCm)} × ${f(depthCm)} ${unit}`;
}

export const formatUsd = (n: number) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);

export const DEFAULT_REQUEST: RoomRequest = {
  widthCm: Math.round(12 * CM_PER_FT),
  depthCm: Math.round(8 * CM_PER_FT),
  roomType: "Living Room",
  theme: "modern",
  budgetUsd: 2000,
};

const clamp = (n: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, n));

export function requestFromParams(params: URLSearchParams): RoomRequest {
  const num = (key: string, fallback: number) => {
    const v = Number(params.get(key));
    return Number.isFinite(v) && v > 0 ? v : fallback;
  };
  const type = params.get("type");
  const theme = params.get("theme");
  return {
    widthCm: clamp(Math.round(num("w", DEFAULT_REQUEST.widthCm)), MIN_ROOM_CM, MAX_ROOM_CM),
    depthCm: clamp(Math.round(num("d", DEFAULT_REQUEST.depthCm)), MIN_ROOM_CM, MAX_ROOM_CM),
    roomType: ROOM_TYPES.includes(type as RoomType) ? (type as RoomType) : DEFAULT_REQUEST.roomType,
    theme: STYLES.includes(theme as StyleTag) ? (theme as StyleTag) : DEFAULT_REQUEST.theme,
    budgetUsd: clamp(Math.round(num("budget", DEFAULT_REQUEST.budgetUsd)), 100, 100000),
  };
}

export function requestToQuery(req: RoomRequest): string {
  const p = new URLSearchParams({
    w: String(req.widthCm),
    d: String(req.depthCm),
    type: req.roomType,
    theme: req.theme,
    budget: String(req.budgetUsd),
  });
  return p.toString();
}