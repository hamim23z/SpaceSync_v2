/* Prompted by Hamim Choudhury - used Claude */

import Link from "next/link";

export const metadata = { title: "Scan room · SpaceSync" };

export default function ScanPage() {
  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-12">
      <span className="rounded-full bg-amber-500/15 px-3 py-1 text-xs font-medium text-amber-700 dark:text-amber-300">
        Coming soon
      </span>
      <h1 className="mt-4 text-3xl font-semibold tracking-tight">Scan your room</h1>
      <p className="mt-3 text-muted">
        Room scanning isn’t built yet. It’s a stretch goal: point your phone around the room and SpaceSync would read
        the floor size for you.
      </p>

      <div className="mt-8 rounded-2xl border border-border bg-surface p-6">
        <h2 className="text-lg font-semibold">For now, measure it yourself</h2>
        <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm text-muted">
          <li>
            Open the <strong>Measure</strong> app on your iPhone (or use a tape measure).
          </li>
          <li>Measure the width and the length of the floor.</li>
          <li>Type those two numbers into the dimensions screen.</li>
        </ol>
        <Link
          href="/dimensions"
          className="mt-6 inline-block rounded-full bg-accent px-6 py-3 text-sm font-semibold text-accent-fg"
        >
          Enter room dimensions
        </Link>
      </div>
    </div>
  );
}