"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import AgentScores from "./AgentScores";
import ArViewer from "./ArViewer";
import ItemCarousel from "./ItemCarousel";
import { getCatalog, getLayout } from "../lib/api";
import { formatSize, formatUsd, requestFromParams, requestToQuery } from "../lib/units";
import { CatalogItem, LayoutResult, STYLES, StyleTag } from "../lib/types";

// three.js needs the browser, so load the canvas on the client only
const RoomCanvas = dynamic(() => import("./RoomCanvas"), {
  ssr: false,
  loading: () => <div className="flex h-full items-center justify-center text-sm text-muted">Loading 3D room…</div>,
});

type Loaded = { key: string; layout?: LayoutResult; catalog?: CatalogItem[]; error?: string };

export default function RoomView() {
  const params = useSearchParams();
  const router = useRouter();
  const req = useMemo(() => requestFromParams(params), [params]);
  const key = requestToQuery(req);

  const [loaded, setLoaded] = useState<Loaded>({ key: "" });
  const [menuOpen, setMenuOpen] = useState(false);
  const [styleFilter, setStyleFilter] = useState<StyleTag[]>([]);
  const [maxPrice, setMaxPrice] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([getLayout(req), getCatalog(req.roomType)])
      .then(([layout, catalog]) => !cancelled && setLoaded({ key: requestToQuery(req), layout, catalog }))
      .catch((e: unknown) => !cancelled && setLoaded({ key: requestToQuery(req), error: e instanceof Error ? e.message : "Something went wrong" }));
    return () => {
      cancelled = true;
    };
  }, [req]);

  const { layout, catalog, error } = loaded.key === key ? loaded : ({} as Loaded);

  const shownItems = useMemo(
    () =>
      (catalog ?? []).filter(
        (it) => (styleFilter.length === 0 || styleFilter.includes(it.style)) && (maxPrice === null || it.price_usd <= maxPrice)
      ),
    [catalog, styleFilter, maxPrice]
  );
  const placedIds = useMemo(() => new Set((layout?.items ?? []).map((p) => p.item_id)), [layout]);
  const priceCeiling = useMemo(() => Math.ceil(Math.max(0, ...(catalog ?? []).map((i) => i.price_usd)) / 50) * 50, [catalog]);
  const setTheme = (theme: StyleTag) => router.replace(`/room?${requestToQuery({ ...req, theme })}`);
  const toggleStyle = (s: StyleTag) => setStyleFilter((cur) => (cur.includes(s) ? cur.filter((x) => x !== s) : [...cur, s]));
  const activeFilters = styleFilter.length + (maxPrice !== null ? 1 : 0);

  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link href="/" className="text-sm text-muted hover:text-foreground">
            ← Home
          </Link>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">Your {req.roomType.toLowerCase()}</h1>
        </div>
        {layout?.source === "mock" && (
          <span className="rounded-full border border-amber-500/40 bg-amber-500/10 px-3 py-1 text-xs font-medium text-amber-700 dark:text-amber-300">
            Demo data: the trained agents aren’t connected yet
          </span>
        )}
      </div>

      {/* 3D room + the "..." filter menu from the sketch */}
      <div className="relative mt-4 h-[380px] overflow-hidden rounded-2xl border border-border bg-surface sm:h-[460px]">
        {error ? (
          <p className="p-6 text-sm text-red-600">{error}</p>
        ) : layout ? (
          <RoomCanvas layout={layout} />
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-muted">Building your room…</div>
        )}

        <div className="absolute right-3 top-3">
          <button
            type="button"
            onClick={() => setMenuOpen((o) => !o)}
            aria-expanded={menuOpen}
            aria-label="Filters"
            className="flex items-center gap-1.5 rounded-full border border-border bg-surface/90 px-3 py-1.5 text-sm font-medium backdrop-blur hover:bg-surface"
          >
            <span aria-hidden>•••</span>
            {activeFilters > 0 && <span className="rounded-full bg-accent px-1.5 text-xs text-accent-fg">{activeFilters}</span>}
          </button>
          {menuOpen && (
            <div className="absolute right-0 mt-2 w-64 rounded-2xl border border-border bg-surface p-4 shadow-xl">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted">Style</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {STYLES.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => toggleStyle(s)}
                    aria-pressed={styleFilter.includes(s)}
                    className={`rounded-full border px-3 py-1 text-xs font-medium capitalize ${
                      styleFilter.includes(s) ? "border-accent bg-accent text-accent-fg" : "border-border hover:bg-background"
                    }`}
                  >
                    {s}
                  </button>
                ))}
              </div>
              <p className="mt-4 text-xs font-semibold uppercase tracking-wide text-muted">
                Max price {maxPrice !== null ? `· ${formatUsd(maxPrice)}` : "· any"}
              </p>
              <input
                type="range"
                min={50}
                max={Math.max(100, priceCeiling)}
                step={10}
                value={maxPrice ?? Math.max(100, priceCeiling)}
                onChange={(e) => setMaxPrice(Number(e.target.value) >= priceCeiling ? null : Number(e.target.value))}
                className="mt-2 w-full accent-[var(--color-accent)]"
                aria-label="Maximum price"
              />
              <div className="mt-4 flex justify-between">
                <button
                  type="button"
                  onClick={() => {
                    setStyleFilter([]);
                    setMaxPrice(null);
                  }}
                  className="text-xs text-muted hover:text-foreground"
                >
                  Clear
                </button>
                <button type="button" onClick={() => setMenuOpen(false)} className="text-xs font-semibold text-accent">
                  Done
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
        <label className="flex items-center gap-2">
          <span className="text-muted">Theme:</span>
          <select
            value={req.theme}
            onChange={(e) => setTheme(e.target.value as StyleTag)}
            className="rounded-lg border border-border bg-surface px-2 py-1 font-medium capitalize"
          >
            {STYLES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <p>
          <span className="text-muted">Dimensions:</span> <span className="font-medium">{formatSize(req.widthCm, req.depthCm)}</span>{" "}
          <Link href={`/dimensions?${key}`} className="text-accent underline-offset-2 hover:underline">
            (change)
          </Link>
        </p>
        <p>
          <span className="text-muted">Budget:</span> <span className="font-medium">{formatUsd(req.budgetUsd)}</span>
          {layout && <span className="text-muted"> · spent {formatUsd(layout.spend_usd)}</span>}
        </p>
      </div>

      {/* scrolling items */}
      <section className="mt-8">
        <div className="mb-3 flex items-baseline justify-between">
          <h2 className="text-lg font-semibold">Pieces for this room</h2>
          <p className="text-xs text-muted">Scroll to see more →</p>
        </div>
        <ItemCarousel items={shownItems} placedIds={placedIds} />
      </section>

      {layout && (
        <section className="mt-8 grid gap-6 lg:grid-cols-[minmax(0,320px)_1fr]">
          <div>
            <h2 className="mb-3 text-lg font-semibold">How each agent scored it</h2>
            <AgentScores layout={layout} />
          </div>
          <div>
            <h2 className="mb-3 text-lg font-semibold">Augmented reality</h2>
            <ArViewer layout={layout} />
          </div>
        </section>
      )}
    </div>
  );
}