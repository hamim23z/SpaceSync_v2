/* Prompted by Hamim Choudhury - used Claude */

import Link from "next/link";

const AGENTS = [
  { name: "Layout", color: "bg-blue-500", text: "Places each piece so it fits, doesn’t overlap, and leaves room to walk." },
  { name: "Style", color: "bg-amber-500", text: "Picks pieces that match your theme and taste." },
  { name: "Budget", color: "bg-emerald-500", text: "Keeps the total under the limit you set." },
];

const STEPS = [
  { title: "Enter your room", text: "Type the room’s size, pick a theme, and set a budget." },
  { title: "Three agents plan it", text: "Specialists for layout, style, and budget work together on one layout." },
  { title: "See it in your room", text: "Rotate it in 3D, then place it on your real floor with augmented reality." },
];

export default function Home() {
  return (
    <>
      <section className="mx-auto w-full max-w-6xl px-4 pb-14 pt-16 sm:pt-24">
        <p className="text-sm font-semibold uppercase tracking-widest text-accent">Multi-agent room planning</p>
        <h1 className="mt-4 max-w-3xl text-4xl font-semibold leading-[1.1] tracking-tight sm:text-6xl">
          Furniture that fits your room, matches your style, and stays on budget.
        </h1>
        <p className="mt-5 max-w-2xl text-lg text-muted">
          SpaceSync uses a team of AI agents to plan how to furnish a room, then lets you preview the result in 3D and
          in augmented reality before you buy anything.
        </p>

        <div className="mt-9 flex flex-wrap gap-3">
          <Link
            href="/dimensions"
            className="rounded-full bg-accent px-7 py-3.5 text-base font-semibold text-accent-fg shadow-sm transition hover:opacity-90"
          >
            Enter room dimensions
          </Link>
          <Link
            href="/scan"
            className="flex items-center gap-2 rounded-full border border-border bg-surface px-7 py-3.5 text-base font-semibold transition hover:bg-background"
          >
            Scan room
            <span className="rounded-full bg-amber-500/15 px-2 py-0.5 text-xs font-medium text-amber-700 dark:text-amber-300">
              coming soon
            </span>
          </Link>
        </div>
      </section>

      <section className="border-y border-border bg-surface">
        <div className="mx-auto grid w-full max-w-6xl gap-4 px-4 py-12 md:grid-cols-3">
          <h2 className="text-2xl font-semibold tracking-tight md:col-span-3">One job per agent</h2>
          {AGENTS.map((a) => (
            <div key={a.name} className="rounded-2xl border border-border bg-background p-5">
              <span className={`inline-block h-2.5 w-2.5 rounded-full ${a.color}`} />
              <h3 className="mt-3 text-lg font-semibold">{a.name} agent</h3>
              <p className="mt-1 text-sm text-muted">{a.text}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mx-auto w-full max-w-6xl px-4 py-14">
        <h2 className="text-2xl font-semibold tracking-tight">How it works</h2>
        <ol className="mt-6 grid gap-4 md:grid-cols-3">
          {STEPS.map((s, i) => (
            <li key={s.title} className="rounded-2xl border border-border bg-surface p-5">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-accent text-sm font-semibold text-accent-fg">
                {i + 1}
              </span>
              <h3 className="mt-3 text-base font-semibold">{s.title}</h3>
              <p className="mt-1 text-sm text-muted">{s.text}</p>
            </li>
          ))}
        </ol>
      </section>

      <footer className="mt-auto border-t border-border">
        <p className="mx-auto w-full max-w-6xl px-4 py-6 text-xs text-muted">
          CSC59867 Senior Design II · Hamim Choudhury &amp; Karthikeya Reddy B · Benchmarking Multi-Agent Reinforcement
          Learning in Augmented Reality
        </p>
      </footer>
    </>
  );
}