import Link from "next/link";
import type { LucideIcon } from "lucide-react";

import { Button } from "@/components/ui";
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
        "border-border bg-card flex flex-col items-center justify-center rounded-xl border text-center",
        fill ? "h-full px-6 py-16" : "px-6 py-20",
        className,
      )}
    >
      {Icon && (
        <div className="bg-muted text-muted-foreground mb-5 flex h-11 w-11 items-center justify-center rounded-xl">
          <Icon className="h-5 w-5" />
        </div>
      )}
      <h3 className="text-foreground font-display text-base font-semibold tracking-tight">{title}</h3>
      {description && (
        <p className="text-muted-foreground mt-1.5 max-w-sm text-sm leading-relaxed text-pretty">
          {description}
        </p>
      )}
      {(cta || secondaryCta) && (
        <div className="mt-6 flex flex-wrap items-center justify-center gap-2">
          {cta && <CtaButton variant="default" {...cta} />}
          {secondaryCta && <CtaButton variant="outline" {...secondaryCta} />}
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
  variant: "default" | "outline";
}) {
  if (href) {
    return (
      <Button asChild variant={variant} size="sm">
        <Link href={href}>{label}</Link>
      </Button>
    );
  }
  return (
    <Button type="button" variant={variant} size="sm" onClick={onClick}>
      {label}
    </Button>
  );
}
