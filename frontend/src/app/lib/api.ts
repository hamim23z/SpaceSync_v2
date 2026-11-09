import { buildMockLayout, mockCatalog } from "./mock";
import { CatalogItem, LayoutResult, RoomRequest, RoomType } from "./types";

/**
 * The only file that knows where the data comes from.
 *
 * Right now there is no backend, so everything is mock data. When Karthikeya's
 * API is ready, set NEXT_PUBLIC_API_URL (e.g. in frontend/.env.local):
 *
 *   NEXT_PUBLIC_API_URL=https://your-api.example.com
 *
 * and these two functions will call it instead. Agreed endpoints (change to match the real ones):
 *   POST {API}/layout           body: RoomRequest            -> LayoutResult
 *   GET  {API}/catalog?room_type=Living%20Room               -> CatalogItem[]
 */
const API = process.env.NEXT_PUBLIC_API_URL;

export async function getLayout(req: RoomRequest): Promise<LayoutResult> {
  if (!API) return buildMockLayout(req);
  const res = await fetch(`${API}/layout`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`Layout request failed (${res.status})`);
  const data = (await res.json()) as LayoutResult;
  return { ...data, source: "api" };
}

export async function getCatalog(roomType: RoomType): Promise<CatalogItem[]> {
  if (!API) return mockCatalog(roomType);
  const res = await fetch(`${API}/catalog?room_type=${encodeURIComponent(roomType)}`);
  if (!res.ok) throw new Error(`Catalog request failed (${res.status})`);
  return (await res.json()) as CatalogItem[];
}