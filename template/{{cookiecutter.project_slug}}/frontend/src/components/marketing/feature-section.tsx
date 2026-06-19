import { Check } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

interface FeatureSectionProps {
  eyebrow: string;
  title: ReactNode;
  description: string;
  bullets?: { title: string; body: string }[];
  visual: ReactNode;
  /** Side the visual sits on at md+. */
  visualSide?: "left" | "right";
  cta?: { label: string; href: string };
}

export function FeatureSection({
  eyebrow,
  title,
  description,
  bullets,
  visual,
  visualSide = "right",
  cta,
}: FeatureSectionProps) {
  return (
    <div
      className={cn(
        "grid items-center gap-12 lg:grid-cols-2 lg:gap-20",
        visualSide === "left" && "lg:[&>:first-child]:order-2",
      )}
    >
      <div>
        <div className="mb-6">
          <span className="eyebrow-badge">{eyebrow}</span>
        </div>
        <h2 className="text-display-lg text-foreground [&_em]:font-accent [&_em]:text-foreground/85 mb-7 [&_em]:font-normal [&_em]:italic">
          {title}
        </h2>
        <p className="text-foreground/75 mb-10 max-w-xl text-xl leading-relaxed">{description}</p>

        {bullets && bullets.length > 0 && (
          <ul className="space-y-5">
            {bullets.map((b) => (
              <li key={b.title} className="flex gap-4">
                <span
                  aria-hidden
                  className="bg-brand/12 text-brand ring-brand/20 mt-0.5 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-lg ring-1"
                >
                  <Check className="h-4 w-4" strokeWidth={2.5} />
                </span>
                <div>
                  <p className="text-foreground font-display text-lg font-semibold">{b.title}</p>
                  <p className="text-foreground/70 mt-1 text-base leading-relaxed">{b.body}</p>
                </div>
              </li>
            ))}
          </ul>
        )}

        {cta && (
          <a
            href={cta.href}
            className="border-foreground/20 hover:border-brand text-foreground mt-12 inline-flex items-center gap-2 border-b pb-1 text-base font-medium transition-colors"
          >
            {cta.label} →
          </a>
        )}
      </div>

      <div className="flex justify-center lg:justify-end">{visual}</div>
    </div>
  );
}
