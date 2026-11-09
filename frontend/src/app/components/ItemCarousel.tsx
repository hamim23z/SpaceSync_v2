import { STYLE_COLORS } from "../lib/scene";
import { formatUsd } from "../lib/units";
import type { CatalogItem } from "../lib/types";

export default function ItemCarousel({ items, placedIds }: { items: CatalogItem[]; placedIds: Set<string> }) {
  if (items.length === 0) {
    return <p className="rounded-2xl border border-dashed border-border p-6 text-sm text-muted">No pieces match these filters.</p>;
  }
  return (
    <div
      className="-mx-4 flex snap-x snap-mandatory gap-3 overflow-x-auto px-4 pb-3"
      role="list"
      aria-label="Furniture pieces for this room"
    >
      {items.map((it) => {
        const inLayout = placedIds.has(it.item_id);
        return (
          <article
            key={it.item_id}
            role="listitem"
            className={`w-52 shrink-0 snap-start rounded-2xl border bg-surface p-3 ${
              inLayout ? "border-accent" : "border-border"
            }`}
          >
            <div
              className="flex h-24 items-end rounded-xl p-2"
              style={{ background: `linear-gradient(135deg, ${STYLE_COLORS[it.style]}33, ${STYLE_COLORS[it.style]}99)` }}
            >
              {inLayout && (
                <span className="rounded-full bg-accent px-2 py-0.5 text-[11px] font-semibold text-accent-fg">In your layout</span>
              )}
            </div>
            <h4 className="mt-3 text-sm font-semibold leading-snug">{it.name}</h4>
            <p className="text-xs text-muted">{it.category}</p>
            <div className="mt-2 flex items-center justify-between">
              <span className="text-sm font-semibold">{formatUsd(it.price_usd)}</span>
              <span
                className="rounded-full px-2 py-0.5 text-[11px] font-medium capitalize text-white"
                style={{ background: STYLE_COLORS[it.style] }}
              >
                {it.style}
              </span>
            </div>
            <p className="mt-1 text-[11px] text-muted">
              {it.width_cm} × {it.depth_cm} × {it.height_cm} cm
            </p>
          </article>
        );
      })}
    </div>
  );
}