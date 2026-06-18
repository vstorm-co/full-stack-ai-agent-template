"use client";

import type { LucideIcon } from "lucide-react";
import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";
import { Area, AreaChart, ResponsiveContainer } from "recharts";

import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: string | number;
  unit?: string;
  /** Percentage delta vs. comparison period. Sign drives the arrow direction. */
  delta?: number;
  /** Description rendered next to delta, e.g. "vs last 7d". */
  deltaLabel?: string;
  /** Sparkline data points; tiny line area chart at the bottom. */
  spark?: number[];
  /** Top-right icon. */
  icon?: LucideIcon;
  /** Visual emphasis — featured cards use the brand surface. */
  featured?: boolean;
  className?: string;
  loading?: boolean;
}

export function StatCard({
  label,
  value,
  unit,
  delta,
  deltaLabel = "vs prior",
  spark,
  icon: Icon,
  featured,
  className,
  loading,
}: StatCardProps) {
  if (loading) {
    return (
      <div
        className={cn(
          "border-border bg-card relative animate-pulse space-y-3 overflow-hidden rounded-2xl border p-5",
          className,
        )}
      >
        <div className="bg-foreground/10 h-3 w-1/3 rounded-full" />
        <div className="bg-foreground/15 h-8 w-1/2 rounded-md" />
        <div className="bg-foreground/8 h-10 w-full rounded-md" />
      </div>
    );
  }

  const trend = typeof delta === "number" ? (delta > 0 ? "up" : delta < 0 ? "down" : "flat") : null;

  return (
    <div
      className={cn(
        "lift relative overflow-hidden rounded-2xl border p-5",
        featured ? "border-brand/40 bg-brand/[0.08]" : "border-border bg-card",
        className,
      )}
    >
      <div className="flex items-start justify-between">
        <p className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">{label}</p>
        {Icon && <Icon className="text-foreground/45 h-4 w-4" />}
      </div>

      <div className="mt-3 flex items-baseline gap-1.5">
        <span className="font-display text-foreground text-3xl font-bold tracking-tight">
          {value}
        </span>
        {unit && <span className="text-foreground/55 text-sm">{unit}</span>}
      </div>

      {trend && (
        <div className="mt-2 flex items-center gap-1.5">
          <span
            className={cn(
              "inline-flex items-center gap-0.5 rounded-full px-2 py-0.5 font-mono text-[11px] font-semibold tabular-nums",
              trend === "up" && "bg-chart/15 text-chart",
              trend === "down" && "bg-destructive/10 text-destructive",
              trend === "flat" && "bg-foreground/8 text-foreground/65",
            )}
          >
            {trend === "up" && <ArrowUpRight className="h-3 w-3" />}
            {trend === "down" && <ArrowDownRight className="h-3 w-3" />}
            {trend === "flat" && <Minus className="h-3 w-3" />}
            {Math.abs(delta!).toFixed(1)}%
          </span>
          <span className="text-foreground/45 font-mono text-[10px] tracking-wider uppercase">
            {deltaLabel}
          </span>
        </div>
      )}

      {spark && spark.length >= 2 && (
        <div className="mt-3 h-10 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={spark.map((v, i) => ({ i, v }))}>
              <defs>
                <linearGradient
                  id={`spark-${label.replace(/\s+/g, "-")}`}
                  x1="0"
                  y1="0"
                  x2="0"
                  y2="1"
                >
                  <stop
                    offset="0%"
                    stopColor="var(--color-brand)"
                    stopOpacity={trend === "down" ? 0 : 0.45}
                  />
                  <stop offset="100%" stopColor="var(--color-brand)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <Area
                type="monotone"
                dataKey="v"
                stroke={trend === "down" ? "var(--color-destructive)" : "var(--color-brand)"}
                strokeWidth={1.5}
                fill={`url(#spark-${label.replace(/\s+/g, "-")})`}
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
