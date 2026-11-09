import { formatUsd } from "../lib/units";
import type { LayoutResult } from "../lib/types";

/** One card per agent, so the "split across specialists" idea is visible on screen. */
export default function AgentScores({ layout }: { layout: LayoutResult }) {
  const { scores, metrics } = layout;
  const cards = [
    {
      name: "Layout agent",
      score: scores.layout,
      color: "bg-blue-500",
      detail: `${Math.round(metrics.utilization * 100)}% of the floor used · ${Math.round(
        metrics.walkway_connectivity * 100
      )}% walkable from the door`,
    },
    {
      name: "Style agent",
      score: scores.style,
      color: "bg-amber-500",
      detail: `${Math.round(metrics.style_similarity * 100)}% match with the “${layout.theme}” theme`,
    },
    {
      name: "Budget agent",
      score: scores.budget,
      color: "bg-emerald-500",
      detail: `${formatUsd(layout.spend_usd)} of ${formatUsd(layout.budget_usd)}${
        layout.spend_usd <= layout.budget_usd ? " · under budget" : " · over budget"
      }`,
    },
  ];

  return (
    <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-1">
      {cards.map((c) => (
        <div key={c.name} className="rounded-2xl border border-border bg-surface p-4">
          <div className="flex items-baseline justify-between">
            <h3 className="text-sm font-semibold">{c.name}</h3>
            <span className="text-2xl font-semibold tabular-nums">{c.score}</span>
          </div>
          <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-background" role="presentation">
            <div className={`h-full rounded-full ${c.color}`} style={{ width: `${c.score}%` }} />
          </div>
          <p className="mt-2 text-xs text-muted">{c.detail}</p>
        </div>
      ))}
    </div>
  );
}