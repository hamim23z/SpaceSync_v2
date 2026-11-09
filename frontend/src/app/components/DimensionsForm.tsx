"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { ROOM_TYPES, RoomType, STYLES, StyleTag } from "../lib/types";
import { MAX_ROOM_CM, MIN_ROOM_CM, Unit, fromCm, requestFromParams, requestToQuery, toCm } from "../lib/units";

const round1 = (n: number) => Math.round(n * 10) / 10;

export default function DimensionsForm() {
  const router = useRouter();
  const initial = requestFromParams(useSearchParams());
  return <Form initial={initial} onSubmit={(q) => router.push(`/room?${q}`)} />;
}

function Form({ initial, onSubmit }: { initial: ReturnType<typeof requestFromParams>; onSubmit: (query: string) => void }) {
  const [unit, setUnit] = useState<Unit>("ft");
  const [width, setWidth] = useState(String(round1(fromCm(initial.widthCm, "ft"))));
  const [length, setLength] = useState(String(round1(fromCm(initial.depthCm, "ft"))));
  const [roomType, setRoomType] = useState<RoomType>(initial.roomType);
  const [theme, setTheme] = useState<StyleTag>(initial.theme);
  const [budget, setBudget] = useState(String(initial.budgetUsd));

  const widthCm = toCm(Number(width), unit);
  const depthCm = toCm(Number(length), unit);
  const limits = `${round1(fromCm(MIN_ROOM_CM, unit))} to ${round1(fromCm(MAX_ROOM_CM, unit))} ${unit}`;
  const sizeOk = (cm: number) => Number.isFinite(cm) && cm >= MIN_ROOM_CM && cm <= MAX_ROOM_CM;
  const budgetNum = Number(budget);
  const valid = sizeOk(widthCm) && sizeOk(depthCm) && Number.isFinite(budgetNum) && budgetNum >= 100;

  const switchUnit = (next: Unit) => {
    if (next === unit) return;
    if (sizeOk(widthCm)) setWidth(String(round1(fromCm(widthCm, next))));
    if (sizeOk(depthCm)) setLength(String(round1(fromCm(depthCm, next))));
    setUnit(next);
  };

  // little floor plan that follows what you type
  const planW = sizeOk(widthCm) ? widthCm : 360;
  const planD = sizeOk(depthCm) ? depthCm : 240;
  const scale = 220 / Math.max(planW, planD);

  return (
    <form
      className="grid gap-8 lg:grid-cols-[1fr_320px]"
      onSubmit={(e) => {
        e.preventDefault();
        if (!valid) return;
        onSubmit(
          requestToQuery({
            widthCm: Math.round(widthCm),
            depthCm: Math.round(depthCm),
            roomType,
            theme,
            budgetUsd: Math.round(budgetNum),
          })
        );
      }}
    >
      <div className="space-y-6">
        <fieldset>
          <legend className="text-sm font-semibold">Room type</legend>
          <div className="mt-2 flex flex-wrap gap-2">
            {ROOM_TYPES.map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setRoomType(t)}
                aria-pressed={roomType === t}
                className={`rounded-full border px-4 py-2 text-sm font-medium ${
                  roomType === t ? "border-accent bg-accent text-accent-fg" : "border-border bg-surface hover:bg-background"
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </fieldset>

        <fieldset>
          <div className="flex items-center justify-between">
            <legend className="text-sm font-semibold">Room size</legend>
            <div className="flex rounded-full border border-border p-0.5 text-xs font-medium" role="group" aria-label="Units">
              {(["ft", "m"] as Unit[]).map((u) => (
                <button
                  key={u}
                  type="button"
                  onClick={() => switchUnit(u)}
                  aria-pressed={unit === u}
                  className={`rounded-full px-3 py-1 ${unit === u ? "bg-accent text-accent-fg" : "text-muted"}`}
                >
                  {u === "ft" ? "feet" : "meters"}
                </button>
              ))}
            </div>
          </div>
          <div className="mt-2 grid grid-cols-2 gap-3">
            <label className="block">
              <span className="text-xs text-muted">Width ({unit})</span>
              <input
                inputMode="decimal"
                value={width}
                onChange={(e) => setWidth(e.target.value)}
                aria-invalid={!sizeOk(widthCm)}
                className="mt-1 w-full rounded-xl border border-border bg-surface px-3 py-2.5 text-base"
              />
            </label>
            <label className="block">
              <span className="text-xs text-muted">Length ({unit})</span>
              <input
                inputMode="decimal"
                value={length}
                onChange={(e) => setLength(e.target.value)}
                aria-invalid={!sizeOk(depthCm)}
                className="mt-1 w-full rounded-xl border border-border bg-surface px-3 py-2.5 text-base"
              />
            </label>
          </div>
          <p className={`mt-2 text-xs ${valid || (sizeOk(widthCm) && sizeOk(depthCm)) ? "text-muted" : "text-red-600"}`}>
            Each side should be {limits}.
          </p>
        </fieldset>

        <fieldset>
          <legend className="text-sm font-semibold">Theme</legend>
          <div className="mt-2 flex flex-wrap gap-2">
            {STYLES.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => setTheme(s)}
                aria-pressed={theme === s}
                className={`rounded-full border px-4 py-2 text-sm font-medium capitalize ${
                  theme === s ? "border-accent bg-accent text-accent-fg" : "border-border bg-surface hover:bg-background"
                }`}
              >
                {s}
              </button>
            ))}
          </div>
        </fieldset>

        <label className="block">
          <span className="block text-sm font-semibold">Budget (USD)</span>
          <input
            inputMode="numeric"
            value={budget}
            onChange={(e) => setBudget(e.target.value.replace(/[^0-9]/g, ""))}
            className="mt-2 w-full max-w-xs rounded-xl border border-border bg-surface px-3 py-2.5 text-base"
          />
          <span className="mt-1 block text-xs text-muted">A limit to stay under, not a number to spend.</span>
        </label>

        <button
          type="submit"
          disabled={!valid}
          className="rounded-full bg-accent px-6 py-3 text-sm font-semibold text-accent-fg disabled:cursor-not-allowed disabled:opacity-40"
        >
          Build my room
        </button>
      </div>

      <aside className="space-y-4">
        <div className="rounded-2xl border border-border bg-surface p-5">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted">Floor plan</p>
          <svg viewBox="0 0 260 260" className="mt-3 w-full" role="img" aria-label="Floor plan preview">
            <rect
              x={(260 - planW * scale) / 2}
              y={(260 - planD * scale) / 2}
              width={planW * scale}
              height={planD * scale}
              rx="4"
              className="fill-background stroke-accent"
              strokeWidth="2"
            />
            <rect
              x={(260 - planW * scale) / 2 + (planW * scale) / 2 - 14}
              y={(260 + planD * scale) / 2 - 3}
              width="28"
              height="6"
              rx="2"
              fill="#16a34a"
            />
          </svg>
          <p className="mt-1 text-center text-xs text-muted">Green mark = door</p>
        </div>
        <div className="rounded-2xl border border-border bg-surface p-5 text-sm">
          <p className="font-semibold">Don’t know your room size?</p>
          <p className="mt-1 text-muted">
            Use your phone’s built-in <strong>Measure</strong> app (iPhone) or a tape measure, then type the numbers in.
            Room scanning is on the way.
          </p>
        </div>
      </aside>
    </form>
  );
}