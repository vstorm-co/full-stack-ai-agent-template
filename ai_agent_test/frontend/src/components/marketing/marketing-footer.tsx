import Link from "next/link";

interface FooterColumn {
  title: string;
  links: { label: string; href: string }[];
}

interface MarketingFooterProps {
  brand: string;
  tagline?: string;
  /** Status badge text (e.g. "All systems operational"). Translated by caller. */
  operationalLabel?: string;
  columns: FooterColumn[];
  legal?: { label: string; href: string }[];
}

export function MarketingFooter({
  brand,
  tagline,
  operationalLabel = "All systems operational",
  columns,
  legal = [],
}: MarketingFooterProps) {
  return (
    <footer className="theme-dark bg-background text-foreground grain relative overflow-hidden">
      {/* Glowing brand-color sphere — the visual anchor */}
      <div
        aria-hidden
        className="pointer-events-none absolute top-1/2 left-1/2 -z-10 h-[760px] w-[760px] -translate-x-1/2 -translate-y-1/2 rounded-full blur-3xl"
        style={{
          background:
            "radial-gradient(circle, oklch(from var(--color-brand) l c h / 0.4), oklch(from var(--color-brand) l c h / 0.08) 50%, transparent 70%)",
        }}
      />

      {/* Concentric rings — depth */}
      <div
        aria-hidden
        className="border-foreground/10 pointer-events-none absolute top-1/2 left-1/2 -z-10 h-[440px] w-[440px] -translate-x-1/2 -translate-y-1/2 rounded-full border"
      />
      <div
        aria-hidden
        className="border-foreground/5 pointer-events-none absolute top-1/2 left-1/2 -z-10 h-[640px] w-[640px] -translate-x-1/2 -translate-y-1/2 rounded-full border"
      />
      <div
        aria-hidden
        className="border-foreground/[0.03] pointer-events-none absolute top-1/2 left-1/2 -z-10 h-[880px] w-[880px] -translate-x-1/2 -translate-y-1/2 rounded-full border"
      />

      {/* Dot grid — masked at edges by the .bg-dots utility */}
      <div aria-hidden className="bg-dots pointer-events-none absolute inset-0 -z-10" />

      <div className="relative mx-auto w-full max-w-5xl px-6 py-28 md:px-10 md:py-36">
        {/* Glass card with the brand + columns */}
        <div className="border-foreground/12 bg-card/40 mx-auto max-w-3xl rounded-3xl border p-10 shadow-2xl backdrop-blur-xl md:p-14">
          <Link
            href="/"
            className="font-display text-foreground flex items-center justify-center gap-3 text-3xl font-bold tracking-tight md:text-4xl"
          >
            <span
              aria-hidden
              className="bg-brand inline-block h-3.5 w-3.5 animate-pulse rounded-full"
              style={{ boxShadow: "0 0 24px var(--color-brand), 0 0 8px var(--color-brand)" }}
            />
            {brand}
          </Link>

          {tagline && (
            <p className="text-foreground/70 mx-auto mt-5 max-w-md text-center text-base leading-relaxed">
              {tagline}
            </p>
          )}

          <div className="border-foreground/10 mt-10 grid grid-cols-2 gap-x-6 gap-y-10 border-t pt-10 md:grid-cols-3">
            {columns.map((col) => (
              <div key={col.title} className="text-center md:text-left">
                <h3 className="eyebrow text-foreground/55 mb-4">{col.title}</h3>
                <ul className="space-y-2.5">
                  {col.links.map((l) => (
                    <li key={l.href}>
                      <Link
                        href={l.href}
                        className="text-foreground/80 hover:text-foreground text-sm font-medium transition-colors"
                      >
                        {l.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        {/* Bottom row — sits outside the card */}
        <div className="text-foreground/55 mt-12 flex flex-col items-center justify-between gap-5 font-mono text-xs md:flex-row">
          <p className="inline-flex items-center gap-2">
            <span
              className="bg-brand h-1.5 w-1.5 animate-pulse rounded-full"
              style={{ boxShadow: "0 0 10px var(--color-brand)" }}
            />
            {operationalLabel}
          </p>
          <p>
            © {new Date().getFullYear()} {brand}
          </p>
          {legal.length > 0 && (
            <ul className="flex flex-wrap items-center justify-center gap-5">
              {legal.map((l) => (
                <li key={l.href}>
                  <Link
                    href={l.href}
                    className="text-foreground/55 hover:text-foreground/90 transition-colors"
                  >
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </footer>
  );
}
