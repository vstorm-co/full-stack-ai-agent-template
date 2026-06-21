"use client";

import { Area, AreaChart, ResponsiveContainer } from "recharts";

export interface StatCardSparkProps {
  /** Sparkline data points. */
  spark: number[];
  /** Unique gradient id, derived from the card label by the parent. */
  id: string;
}

/**
 * The recharts-powered sparkline, split out of `stat-card.tsx` so the parent (and
 * every page that renders a StatCard) doesn't statically import recharts. Loaded
 * on demand via `next/dynamic` from the parent.
 */
export function StatCardSpark({ spark, id }: StatCardSparkProps) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={spark.map((v, i) => ({ i, v }))}>
        <defs>
          <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--color-foreground)" stopOpacity={0.16} />
            <stop offset="100%" stopColor="var(--color-foreground)" stopOpacity={0} />
          </linearGradient>
        </defs>
        <Area
          type="monotone"
          dataKey="v"
          stroke="var(--color-foreground)"
          strokeOpacity={0.45}
          strokeWidth={1.5}
          fill={`url(#${id})`}
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
