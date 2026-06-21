{% raw %}"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export type UsageMetric = "credits" | "calls" | "tokens";

const METRIC_LABELS: Record<UsageMetric, string> = {
  credits: "Credits",
  calls: "Calls",
  tokens: "Tokens",
};

export interface UsageChartPoint {
  day: string;
  label: string;
  credits: number;
  calls: number;
  tokens: number;
}

export interface UsageTimelineChartProps {
  chartData: UsageChartPoint[];
  metric: UsageMetric;
}

/**
 * The recharts area chart for the usage timeline, split out of
 * `usage-timeline.tsx` so the parent doesn't statically import recharts. Loaded
 * on demand via `next/dynamic`.
 */
export function UsageTimelineChart({ chartData, metric }: UsageTimelineChartProps) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={chartData} margin={{ top: 10, right: 4, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="usage-gradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--color-chart)" stopOpacity={0.35} />
            <stop offset="100%" stopColor="var(--color-chart)" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid
          stroke="oklch(from var(--color-foreground) l c h / 0.06)"
          strokeDasharray="3 3"
          vertical={false}
        />
        <XAxis
          dataKey="label"
          stroke="oklch(from var(--color-foreground) l c h / 0.4)"
          fontSize={11}
          tickLine={false}
          axisLine={false}
          tick={{ fontFamily: "var(--font-mono)" }}
          interval="preserveStartEnd"
        />
        <YAxis
          stroke="oklch(from var(--color-foreground) l c h / 0.4)"
          fontSize={11}
          tickLine={false}
          axisLine={false}
          tick={{ fontFamily: "var(--font-mono)" }}
          width={36}
        />
        <Tooltip
          content={<UsageTooltip metric={metric} />}
          cursor={{ stroke: "var(--color-chart)", strokeOpacity: 0.4 }}
        />
        <Area
          type="monotone"
          dataKey={metric}
          stroke="var(--color-chart)"
          strokeWidth={2}
          fill="url(#usage-gradient)"
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

function UsageTooltip({
  active,
  payload,
  label,
  metric,
}: {
  active?: boolean;
  payload?: Array<{ value: number }>;
  label?: string;
  metric: UsageMetric;
}) {
  const first = payload?.[0];
  if (!active || !first) return null;
  return (
    <div className="border-border bg-card text-foreground rounded-lg border px-3 py-2 text-xs shadow-lg">
      <p className="text-foreground/55 font-mono text-[10px] tracking-wider uppercase">{label}</p>
      <p className="mt-1 font-semibold">
        {first.value.toLocaleString()} {METRIC_LABELS[metric].toLowerCase()}
      </p>
    </div>
  );
}
{% endraw %}
