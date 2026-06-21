{% raw %}import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import type { ReactNode } from "react";

import { AnimatedNumber } from "./animated-number";

interface FinalCtaProps {
  /** Big animated stat displayed above the headline. */
  stat: { value: string; label: string };
  /** Headline below the stat — supports `<em>` for italic accent. */
  title: ReactNode;
  /** Optional reassurance line under the buttons. */
  description?: string;
  primary: { label: string; href: string };
  secondary?: { label: string; href: string };
}

export function FinalCta({ stat, title, description, primary, secondary }: FinalCtaProps) {
  return (
    <div className="border-foreground/10 bg-foreground/[0.02] relative isolate overflow-hidden rounded-3xl border px-8 py-20 md:px-16 md:py-28">
      <div
        aria-hidden
        className="pointer-events-none absolute top-1/3 -left-40 -z-10 h-[460px] w-[460px] rounded-full blur-3xl"
        style={{
          background:
            "radial-gradient(circle, oklch(from var(--color-brand) l c h / 0.35), transparent 65%)",
        }}
      />
      <div aria-hidden className="bg-dots pointer-events-none absolute inset-0 -z-10 opacity-60" />

      <div className="max-w-3xl">
        <div className="eyebrow text-foreground/55 mb-6 flex items-center gap-2">
          <span
            aria-hidden
            className="bg-brand h-1.5 w-1.5 animate-pulse rounded-full"
            style={{ boxShadow: "0 0 12px var(--color-brand)" }}
          />
          {stat.label}
        </div>

        <div className="text-foreground font-mono text-[clamp(4.5rem,16vw,11rem)] leading-[0.9] font-medium tracking-tighter">
          <AnimatedNumber value={stat.value} durationMs={1400} />
        </div>

        <h2 className="text-display-lg text-foreground/85 [&_em]:font-accent mt-10 max-w-2xl [&_em]:font-normal [&_em]:italic">
          {title}
        </h2>

        <div className="mt-10 flex flex-wrap items-center gap-3">
          <Link
            href={primary.href}
            className="bg-foreground text-background hover:bg-foreground/90 group inline-flex items-center gap-3 rounded-full py-2 pr-2 pl-6 text-base font-medium transition-colors"
          >
            <span>{primary.label}</span>
            <span className="bg-brand text-brand-foreground flex h-9 w-9 items-center justify-center rounded-full transition-transform group-hover:rotate-45">
              <ArrowUpRight className="h-4 w-4" />
            </span>
          </Link>
          {secondary && (
            <Link
              href={secondary.href}
              className="border-foreground/20 hover:border-foreground/50 text-foreground inline-flex items-center gap-2 rounded-full border px-5 py-2.5 text-base font-medium transition-colors"
            >
              {secondary.label}
            </Link>
          )}
        </div>

        {description && <p className="text-foreground/55 mt-6 font-mono text-xs">{description}</p>}
      </div>
    </div>
  );
}
{% endraw %}
