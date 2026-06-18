import Link from "next/link";
import { ArrowUpRight, Database, MessageSquare, Sparkles, Wrench } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

import { AnimatedNumber } from "./animated-number";
import { HeroDemo } from "./hero-demo";
import { Section } from "./section";

interface HeroStats {
  value: string;
  label: string;
}

interface HeroCta {
  label: string;
  href: string;
}

interface HeroProps {
  eyebrow?: string;
  /** Headline supports `<em>` for italic accent emphasis. */
  title: ReactNode;
  description: string;
  primaryCta: HeroCta;
  secondaryCta?: HeroCta;
  stats?: HeroStats[];
  theme?: "light" | "dark";
}

const FLOAT_PILLS = [
  {
    icon: MessageSquare,
    label: "Real-time chat",
    className: "left-[-12px] top-12 md:left-[-32px] md:top-16 float-y",
  },
  {
    icon: Database,
    label: "Connected to your data",
    className: "right-[-8px] top-24 md:right-[-40px] md:top-28 float-y-delayed",
  },
  {
    icon: Wrench,
    label: "Acts on your behalf",
    className: "left-[8%] bottom-[-18px] md:left-[12%] md:bottom-[-24px] float-y-delayed",
  },
  {
    icon: Sparkles,
    label: "Always on",
    className: "right-[10%] bottom-[-12px] md:right-[12%] md:bottom-[-20px] float-y",
  },
];

export function Hero({
  eyebrow,
  title,
  description,
  primaryCta,
  secondaryCta,
  stats,
  theme = "dark",
}: HeroProps) {
  return (
    <Section
      theme={theme}
      padding="pt-28 pb-20 md:pt-32 md:pb-28"
      className="spotlight-bg grain relative overflow-hidden"
    >
      {/* Subtle background grid — sits under everything */}
      <div aria-hidden className="bg-grid pointer-events-none absolute inset-0 -z-10" />
      {/* Centered text block */}
      <div className="flex flex-col items-center text-center">
        {eyebrow && (
          <div className="eyebrow text-foreground/65 mb-8">
            <span
              aria-hidden
              className="bg-brand mr-2 inline-block h-1.5 w-1.5 rounded-full align-middle"
            />
            {eyebrow}
          </div>
        )}

        <h1 className="text-display-2xl text-foreground [&_em]:font-accent [&_em]:text-foreground/85 max-w-4xl [&_em]:font-normal [&_em]:italic">
          {title}
        </h1>

        <p className="text-foreground/75 mt-8 max-w-xl text-xl leading-relaxed">{description}</p>

        <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
          <Link
            href={primaryCta.href}
            className="bg-foreground text-background hover:bg-foreground/90 group inline-flex items-center gap-3 rounded-full py-2.5 pr-2 pl-7 text-base font-medium transition-colors"
          >
            <span>{primaryCta.label}</span>
            <span className="bg-brand text-brand-foreground flex h-9 w-9 items-center justify-center rounded-full transition-transform group-hover:rotate-45">
              <ArrowUpRight className="h-4 w-4" />
            </span>
          </Link>
          {secondaryCta && (
            <Link
              href={secondaryCta.href}
              className="border-foreground/20 hover:border-foreground/50 text-foreground inline-flex items-center gap-2 rounded-full border px-6 py-3 text-base font-medium transition-colors"
            >
              {secondaryCta.label}
            </Link>
          )}
        </div>
      </div>

      {/* Demo block with floating accent pills */}
      <div className="relative mt-16 md:mt-20">
        {/* Soft glow under demo */}
        <div
          aria-hidden
          className="absolute inset-x-12 top-1/4 -z-10 h-1/2 rounded-full blur-3xl"
          style={{ background: "oklch(from var(--color-brand) l c h / 0.18)" }}
        />

        <div className="tilt-3d transition-transform">
          <HeroDemo />
        </div>

        {FLOAT_PILLS.map((pill) => (
          <div
            key={pill.label}
            className={cn(
              "border-foreground/15 bg-card text-foreground absolute hidden items-center gap-2 rounded-full border px-3 py-1.5 text-sm font-medium shadow-lg backdrop-blur md:inline-flex",
              pill.className,
            )}
          >
            <span className="bg-brand text-brand-foreground flex h-6 w-6 items-center justify-center rounded-full">
              <pill.icon className="h-3.5 w-3.5" />
            </span>
            {pill.label}
          </div>
        ))}
      </div>

      {/* Stats horizontal band — credibility footer for hero */}
      {stats && stats.length > 0 && (
        <dl className="border-foreground/10 mx-auto mt-20 grid max-w-4xl grid-cols-3 divide-x divide-[color-mix(in_oklab,var(--color-foreground)_12%,transparent)] border-t border-b py-8 md:mt-24">
          {stats.map((stat) => (
            <div key={stat.label} className="px-4 text-center md:px-8">
              <dt className="text-foreground font-mono text-3xl font-medium tracking-tight md:text-4xl">
                <AnimatedNumber value={stat.value} />
              </dt>
              <dd className="eyebrow text-foreground/55 mt-2">{stat.label}</dd>
            </div>
          ))}
        </dl>
      )}
    </Section>
  );
}
