import Link from "next/link";
import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  cta?: { label: string; href?: string; onClick?: () => void };
  secondaryCta?: { label: string; href?: string; onClick?: () => void };
  className?: string;
  /** When true, fills its parent (use inside a flex/grid cell). Default: tall padding. */
  fill?: boolean;
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  cta,
  secondaryCta,
  className,
  fill,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "border-foreground/10 bg-card flex flex-col items-center justify-center rounded-2xl border-2 border-dashed text-center",
        fill ? "h-full px-6 py-16" : "px-6 py-20",
        className,
      )}
    >
      {Icon && (
        <div className="bg-brand/15 text-foreground mb-5 flex h-12 w-12 items-center justify-center rounded-full">
          <Icon className="h-5 w-5" />
        </div>
      )}
      <h3 className="font-display text-foreground text-lg font-semibold tracking-tight">{title}</h3>
      {description && (
        <p className="text-foreground/60 mt-2 max-w-sm text-sm leading-relaxed">{description}</p>
      )}
      {(cta || secondaryCta) && (
        <div className="mt-6 flex flex-wrap items-center justify-center gap-2">
          {cta && <CtaButton variant="primary" {...cta} />}
          {secondaryCta && <CtaButton variant="secondary" {...secondaryCta} />}
        </div>
      )}
    </div>
  );
}

function CtaButton({
  label,
  href,
  onClick,
  variant,
}: {
  label: string;
  href?: string;
  onClick?: () => void;
  variant: "primary" | "secondary";
}) {
  const className = cn(
    "inline-flex items-center justify-center rounded-full px-5 py-2 text-sm font-medium transition-colors",
    variant === "primary"
      ? "bg-foreground text-background hover:bg-foreground/90"
      : "border-foreground/20 hover:border-foreground/40 text-foreground border",
  );
  if (href) {
    return (
      <Link href={href} className={className}>
        {label}
      </Link>
    );
  }
  return (
    <button type="button" onClick={onClick} className={className}>
      {label}
    </button>
  );
}
