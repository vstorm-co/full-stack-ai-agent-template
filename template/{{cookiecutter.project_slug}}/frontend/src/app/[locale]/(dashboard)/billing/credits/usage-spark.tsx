{% raw %}"use client";

import { Area, AreaChart, ResponsiveContainer } from "recharts";

export interface UsageSparkPoint {
  i: number;
  v: number;
}

/**
 * The recharts usage sparkline, split out so the credits page doesn't statically
 * import recharts. Loaded on demand via `next/dynamic`.
 */
export function UsageSpark({ data }: { data: UsageSparkPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={data} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
        <Area
          type="monotone"
          dataKey="v"
          stroke="var(--color-brand)"
          strokeWidth={1.5}
          fill="var(--color-brand)"
          fillOpacity={0.08}
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
{% endraw %}
