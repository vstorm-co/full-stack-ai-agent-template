"use client";

import type { ReactNode } from "react";
import dynamic from "next/dynamic";
import type { LucideIcon } from "lucide-react";
import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";

import { cn } from "@/lib/utils";

// Recharts is only needed for the optional sparkline, so it's split into a child
// component and loaded on demand — keeping recharts out of the bundle of every
// page that renders a StatCard without `spark` data.
const StatCardSpark = dynamic(
  () => import("./stat-card-spark").then((m) => m.StatCardSpark),
  { ssr: false, loading: () => <div className="h-full w-full" /> },
);

interface StatCardProps {
  label: string;
  value: string | number;
  unit?: string;
  /** Percentage delta vs. comparison period. Sign drives the arrow direction. */
  delta?: number;
  /** Description rendered next to delta, e.g. "vs last 7d". */
  deltaLabel?: string;
  /**
   * Neutral secondary line shown in the footer row when there is no `delta`.
   * Use for descriptors ("across all chats") or mini metrics so cards without
   * trend data still have an aligned footer. Ignored when `delta` is provided.
   */
  footer?: ReactNode;
  /** Sparkline data points; tiny line area chart at the bottom. */
  spark?: number[];
  /** Top-right icon. */
  icon?: LucideIcon;
  className?: string;
  loading?: boolean;
}

const sparkId = (label: string) => `spark-${label.replace(/[^a-z0-9]+/gi, "-")}`;

export function StatCard({
  label,
  value,
  unit,
  delta,
  deltaLabel = "vs prior",
  footer,
  spark,
  icon: Icon,
  className,
  loading,
}: StatCardProps) {
  if (loading) {
    return (
      <div
        className={cn(
          "border-border bg-card relative animate-pulse space-y-3 overflow-hidden rounded-xl border p-5",
          className,
        )}
      >
        <div className="bg-foreground/10 h-3 w-1/3 rounded-full" />
        <div className="bg-foreground/15 h-7 w-1/2 rounded-md" />
        <div className="bg-foreground/[0.06] h-8 w-full rounded-md" />
      </div>
    );
  }

  const trend = typeof delta === "number" ? (delta > 0 ? "up" : delta < 0 ? "down" : "flat") : null;
  const id = sparkId(label);

  return (
    <div className={cn("border-border bg-card flex flex-col rounded-xl border p-5", className)}>
      <div className="flex items-center justify-between">
        <p className="text-muted-foreground text-xs font-medium">{label}</p>
        {Icon && <Icon className="text-muted-foreground/70 h-4 w-4" />}
      </div>

      <div className="mt-2.5 flex items-baseline gap-1.5">
        <span className="text-foreground font-display text-2xl font-semibold tracking-tight tabular-nums">
          {value}
        </span>
        {unit && <span className="text-muted-foreground text-sm">{unit}</span>}
      </div>

      {/* Footer row — always present so every card has the same vertical
          structure (label/icon → value → footer). Delta wins when available;
          otherwise the neutral `footer` line keeps cards balanced. */}
      <div className="mt-2 flex min-h-[18px] items-center gap-1.5">
        {trend ? (
          <>
            <span
              className={cn(
                "inline-flex items-center gap-0.5 font-mono text-[11px] font-medium tabular-nums",
                trend === "up" ? "text-foreground" : "text-muted-foreground",
              )}
            >
              {trend === "up" && <ArrowUpRight className="h-3 w-3" />}
              {trend === "down" && <ArrowDownRight className="h-3 w-3" />}
              {trend === "flat" && <Minus className="h-3 w-3" />}
              {Math.abs(delta!).toFixed(1)}%
            </span>
            <span className="text-muted-foreground/70 text-[11px]">{deltaLabel}</span>
          </>
        ) : (
          footer && <span className="text-muted-foreground/70 text-[11px]">{footer}</span>
        )}
      </div>

      {spark && spark.length >= 2 && (
        <div className="mt-auto h-9 w-full pt-3">
          <StatCardSpark spark={spark} id={id} />
        </div>
      )}
    </div>
  );
}
