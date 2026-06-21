{% raw %}"use client";

import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

interface UsageGaugeProps {
  label: string;
  /** Current consumption. */
  used: number;
  /** Limit / cap. When undefined or 0, gauge renders as informational only. */
  limit?: number;
  /** Unit shown next to the numbers (e.g. "credits", "GB"). */
  unit?: string;
  /** Display formatter for numbers. Defaults to locale-aware number string. */
  format?: (value: number) => string;
  icon?: LucideIcon;
  /** Custom warning threshold (0-1). Default 0.7. */
  warnAt?: number;
  /** Custom danger threshold (0-1). Default 0.9. */
  dangerAt?: number;
  /** Subdued caption under the bar. */
  hint?: string;
  className?: string;
}

export function UsageGauge({
  label,
  used,
  limit,
  unit,
  format,
  icon: Icon,
  warnAt = 0.7,
  dangerAt = 0.9,
  hint,
  className,
}: UsageGaugeProps) {
  const fmt = format ?? ((n: number) => n.toLocaleString());
  const hasLimit = typeof limit === "number" && limit > 0;
  const ratio = hasLimit ? Math.min(1, Math.max(0, used / limit)) : 0;
  const pct = ratio * 100;

  const tone = !hasLimit
    ? "neutral"
    : ratio >= dangerAt
      ? "danger"
      : ratio >= warnAt
        ? "warn"
        : "ok";

  const fillClass =
    tone === "danger" ? "bg-destructive" : tone === "warn" ? "bg-yellow-500" : "bg-brand";

  const labelClass =
    tone === "danger"
      ? "text-destructive"
      : tone === "warn"
        ? "text-yellow-500"
        : "text-foreground/55";

  return (
    <div className={cn("border-foreground/10 bg-card rounded-2xl border p-5", className)}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">
            {label}
          </p>
          <div className="mt-2 flex items-baseline gap-1.5">
            <span className="font-display text-foreground text-2xl font-bold">{fmt(used)}</span>
            {hasLimit && (
              <span className="text-foreground/55 text-sm">
                / {fmt(limit!)}
                {unit && ` ${unit}`}
              </span>
            )}
            {!hasLimit && unit && <span className="text-foreground/55 text-sm">{unit}</span>}
          </div>
        </div>
        {Icon && <Icon className="text-foreground/45 h-4 w-4" />}
      </div>

      {hasLimit && (
        <>
          <div
            role="progressbar"
            aria-valuenow={pct}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={label}
            className="bg-foreground/8 mt-4 h-2 w-full overflow-hidden rounded-full"
          >
            <div
              className={`h-full rounded-full transition-all duration-500 ease-out ${fillClass}`}
              style={{ width: `${pct}%` }}
            />
          </div>
          <div className="mt-2 flex items-center justify-between font-mono text-[10px] tracking-wider uppercase">
            <span className={labelClass}>{pct.toFixed(pct >= 10 ? 0 : 1)}% used</span>
            <span className="text-foreground/45">{fmt(Math.max(0, limit! - used))} left</span>
          </div>
        </>
      )}

      {hint && <p className="text-foreground/55 mt-3 text-xs leading-relaxed">{hint}</p>}
    </div>
  );
}
{% endraw %}
