import Link from "next/link";

export default function SiteHeader() {
  return (
    <header className="border-b border-border bg-surface/80 backdrop-blur">
      <div className="mx-auto flex h-14 w-full max-w-6xl items-center justify-between px-4">
        <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden>
            <rect x="3" y="3" width="18" height="18" rx="4" className="stroke-accent" strokeWidth="2" />
            <rect x="7" y="7" width="6" height="4" rx="1" className="fill-accent" />
            <rect x="13" y="13" width="4" height="4" rx="1" className="fill-accent" opacity="0.55" />
          </svg>
          SpaceSync
        </Link>
        <nav className="flex items-center gap-1 text-sm">
          <Link href="/dimensions" className="rounded-full px-3 py-1.5 text-muted hover:bg-background hover:text-foreground">
            Enter dimensions
          </Link>
          <Link href="/scan" className="rounded-full px-3 py-1.5 text-muted hover:bg-background hover:text-foreground">
            Scan room
          </Link>
        </nav>
      </div>
    </header>
  );
}