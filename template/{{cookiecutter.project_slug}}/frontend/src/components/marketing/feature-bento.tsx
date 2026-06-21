{% raw %}import Link from "next/link";
import { ArrowUpRight, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

interface BentoBullet {
  title: string;
  body: string;
  icon: LucideIcon;
}

interface FeatureBentoProps {
  eyebrow: string;
  /** Headline supports `<em>` for italic accent emphasis. */
  title: ReactNode;
  description: string;
  cta?: { label: string; href: string };
  /** Product mini-UI shown in the large cell. */
  mockup: ReactNode;
  /** Punchy metric card. */
  stat: { value: string; label: string };
  /** Exactly three benefit cards. */
  bullets: [BentoBullet, BentoBullet, BentoBullet];
  /** Which side the large mockup sits on at md+. */
  mockupSide?: "left" | "right";
}

const CARD =
  "group border-foreground/12 bg-card lift hover:border-foreground/25 relative overflow-hidden rounded-2xl border transition-colors";

function BulletCard({
  b,
  layout,
  className,
}: {
  b: BentoBullet;
  layout: "row" | "stack";
  className?: string;
}) {
  return (
    <div
      className={cn(
        CARD,
        "p-6",
        layout === "row" ? "flex items-center gap-5" : "flex flex-col justify-center",
        className,
      )}
    >
      <span
        aria-hidden
        className="bg-brand/12 text-brand ring-brand/20 inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ring-1"
      >
        <b.icon className="h-5 w-5" strokeWidth={2} />
      </span>
      <div className={layout === "stack" ? "mt-4" : ""}>
        <p className="text-foreground font-display text-base font-bold">{b.title}</p>
        <p className="text-foreground/65 mt-1 text-sm leading-relaxed">{b.body}</p>
      </div>
    </div>
  );
}

export function FeatureBento({
  eyebrow,
  title,
  description,
  cta,
  mockup,
  stat,
  bullets,
  mockupSide = "right",
}: FeatureBentoProps) {
  const intro = (
    <div className={cn(CARD, "md:col-span-2 md:row-span-2", "flex flex-col p-7")}>
      <span className="eyebrow-badge mb-5 self-start">{eyebrow}</span>
      <h2 className="text-display-md text-foreground [&_em]:font-accent [&_em]:text-foreground/85 [&_em]:font-normal [&_em]:italic">
        {title}
      </h2>
      <p className="text-foreground/70 mt-4 text-base leading-relaxed">{description}</p>
      {cta && (
        <Link
          href={cta.href}
          className="text-foreground hover:text-brand group/cta mt-auto inline-flex items-center gap-1.5 pt-6 text-sm font-medium"
        >
          {cta.label}
          <ArrowUpRight className="h-4 w-4 transition-transform group-hover/cta:translate-x-0.5 group-hover/cta:-translate-y-0.5" />
        </Link>
      )}
    </div>
  );

  const visual = (
    <div
      className={cn(CARD, "md:col-span-4 md:row-span-2", "flex items-center justify-center p-6")}
    >
      <div
        aria-hidden
        className="pointer-events-none absolute -top-20 left-1/2 -z-0 h-72 w-72 -translate-x-1/2 rounded-full blur-3xl"
        style={{ background: "oklch(from var(--color-brand) l c h / 0.16)" }}
      />
      <div aria-hidden className="bg-dots pointer-events-none absolute inset-0 -z-0 opacity-40" />
      <div className="relative z-10 w-full">{mockup}</div>
    </div>
  );

  const statCard = (
    <div className={cn(CARD, "md:col-span-2", "flex flex-col justify-center p-7")}>
      <div className="text-foreground font-mono text-5xl font-medium tracking-tight tabular-nums">
        {stat.value}
      </div>
      <p className="text-foreground/55 eyebrow mt-3">{stat.label}</p>
    </div>
  );

  return (
    <div className="grid grid-cols-1 gap-4 md:auto-rows-[190px] md:grid-cols-6">
      {mockupSide === "left" ? (
        <>
          {visual}
          {intro}
        </>
      ) : (
        <>
          {intro}
          {visual}
        </>
      )}

      {statCard}
      <BulletCard b={bullets[0]} layout="row" className="md:col-span-4" />
      <BulletCard b={bullets[1]} layout="stack" className="md:col-span-3" />
      <BulletCard b={bullets[2]} layout="stack" className="md:col-span-3" />
    </div>
  );
}
{% endraw %}
