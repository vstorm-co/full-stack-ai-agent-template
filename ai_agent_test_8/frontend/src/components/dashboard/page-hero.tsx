import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import Link from "next/link";
import { ArrowUpRight, Plus } from "lucide-react";

import { cn } from "@/lib/utils";

interface HeroStat {
  value: string | number;
  label: string;
}

interface HeroCta {
  label: string;
  href?: string;
  onClick?: () => void;
  /** Optional icon shown in the brand pill (defaults to ArrowUpRight). */
  icon?: LucideIcon;
}

interface PageHeroProps {
  eyebrow: string;
  /** Headline supports `<em>` for italic Bricolage accent. */
  title: ReactNode;
  description?: string;
  /** Optional mono-pills row of stats. */
  stats?: HeroStat[];
  /** Optional primary CTA pill on the bottom. */
  cta?: HeroCta;
  /** Optional secondary actions in the top-right corner. */
  actions?: ReactNode;
  /** Tone of the corner glow — brand (default) or destructive. */
  tone?: "brand" | "destructive";
  className?: string;
}

/**
 * Shared hero card for dashboard pages. Provides a consistent visual anchor:
 * rounded-3xl bordered card with a corner brand-glow, dot-grid texture,
 * eyebrow + display title (with `<em>` italic accent) + optional description,
 * optional stat pills row, and optional primary CTA + actions slot.
 */
export function PageHero({
  eyebrow,
  title,
  description,
  stats,
  cta,
  actions,
  tone = "brand",
  className,
}: PageHeroProps) {
  const glowColor = tone === "destructive" ? "var(--color-destructive)" : "var(--color-brand)";

  const CtaIcon = cta?.icon ?? ArrowUpRight;

  const ctaContent = cta && (
    <span className="group inline-flex items-center gap-3 rounded-full">
      <span>{cta.label}</span>
      <span
        className={cn(
          "flex h-8 w-8 items-center justify-center rounded-full transition-transform",
          cta.icon === Plus ? "group-hover:rotate-90" : "group-hover:rotate-45",
          tone === "destructive"
            ? "bg-destructive text-destructive-foreground"
            : "bg-brand text-brand-foreground",
        )}
      >
        <CtaIcon className="h-4 w-4" />
      </span>
    </span>
  );

  return (
    <header
      className={cn(
        "border-foreground/10 bg-foreground/[0.02] relative isolate overflow-hidden rounded-3xl border p-7 sm:p-9",
        className,
      )}
    >
      <div
        aria-hidden
        className="pointer-events-none absolute -top-24 -right-24 -z-10 h-[340px] w-[340px] rounded-full blur-3xl"
        style={{
          background: `radial-gradient(circle, oklch(from ${glowColor} l c h / 0.26), transparent 65%)`,
        }}
      />
      <div aria-hidden className="bg-dots pointer-events-none absolute inset-0 -z-10 opacity-50" />

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <p className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">
            {eyebrow}
          </p>
          <h1 className="font-display text-foreground [&_em]:font-accent mt-2 text-3xl leading-[1.05] font-bold tracking-tight sm:text-4xl [&_em]:font-normal [&_em]:italic">
            {title}
          </h1>
          {description && <p className="text-foreground/65 mt-4 max-w-xl text-sm">{description}</p>}
        </div>
        {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
      </div>

      {stats && stats.length > 0 && (
        <div className="text-foreground/55 mt-6 flex flex-wrap items-center gap-x-6 gap-y-2 font-mono text-[11px] tracking-wider uppercase">
          {stats.map((s) => (
            <span key={s.label} className="inline-flex items-baseline gap-1.5">
              <span className="text-foreground text-base tabular-nums">{s.value}</span>
              <span>{s.label}</span>
            </span>
          ))}
        </div>
      )}

      {cta && (
        <div className="mt-7">
          {cta.href ? (
            <Link
              href={cta.href}
              className={cn(
                "inline-flex items-center transition-colors",
                tone === "destructive"
                  ? "bg-destructive text-destructive-foreground hover:bg-destructive/90"
                  : "bg-foreground text-background hover:bg-foreground/90",
                "rounded-full py-2 pr-2 pl-5 text-sm font-medium",
              )}
            >
              {ctaContent}
            </Link>
          ) : (
            <button
              type="button"
              onClick={cta.onClick}
              className={cn(
                "inline-flex items-center transition-colors",
                tone === "destructive"
                  ? "bg-destructive text-destructive-foreground hover:bg-destructive/90"
                  : "bg-foreground text-background hover:bg-foreground/90",
                "rounded-full py-2 pr-2 pl-5 text-sm font-medium",
              )}
            >
              {ctaContent}
            </button>
          )}
        </div>
      )}
    </header>
  );
}
