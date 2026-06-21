import * as React from "react";

import { cn } from "@/lib/utils";

export interface SectionHeadingProps {
  /** Small mono "kicker" above the title — the editorial-technical signature. */
  eyebrow?: React.ReactNode;
  title: React.ReactNode;
  description?: React.ReactNode;
  /** Right-aligned actions (buttons, links). */
  actions?: React.ReactNode;
  className?: string;
}

/**
 * In-card / in-section heading that mirrors the page-level PageHeader signature
 * (mono uppercase kicker + confident title) one level down. Use for the heading
 * row inside cards/panels so section titles read consistently across the app.
 */
export function SectionHeading({
  eyebrow,
  title,
  description,
  actions,
  className,
}: SectionHeadingProps) {
  return (
    <div className={cn("flex items-start justify-between gap-3", className)}>
      <div className="min-w-0">
        {eyebrow && (
          <p className="text-muted-foreground mb-1 font-mono text-[11px] font-medium tracking-[0.1em] uppercase">
            {eyebrow}
          </p>
        )}
        <h2 className="text-foreground text-sm font-semibold tracking-tight">{title}</h2>
        {description && (
          <p className="text-muted-foreground mt-0.5 text-xs leading-relaxed">{description}</p>
        )}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  );
}
