{% raw %}"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const TOOLTIP_STYLE = {
  background: "var(--color-popover)",
  border: "1px solid var(--color-border)",
  borderRadius: "8px",
  fontSize: "12px",
} as const;

// Flat, mono legend matching the token-based chart styling.
const LEGEND_STYLE = {
  fontSize: "11px",
  fontFamily: "var(--font-mono, ui-monospace, monospace)",
  paddingTop: "8px",
} as const;

export interface TimelinePoint {
  day: string;
  credits: number;
  calls: number;
}

export interface ByModelPoint {
  name: string;
  input: number;
  output: number;
  credits: number;
}

/**
 * The recharts daily-credits line chart, split out so the usage page doesn't
 * statically import recharts. Loaded on demand via `next/dynamic`.
 */
export function DailyCreditsChart({ data }: { data: TimelinePoint[] }) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={data} margin={{ top: 4, right: 4, bottom: 4, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
        <XAxis
          dataKey="day"
          tick={{ fontSize: 11, fill: "var(--color-muted-foreground)" }}
          stroke="var(--color-border)"
          interval="preserveStartEnd"
        />
        <YAxis
          tick={{ fontSize: 11, fill: "var(--color-muted-foreground)" }}
          stroke="var(--color-border)"
        />
        <Tooltip contentStyle={TOOLTIP_STYLE} />
        <Legend wrapperStyle={LEGEND_STYLE} iconType="plainline" />
        <Line
          type="monotone"
          dataKey="credits"
          name="Credits"
          stroke="var(--color-brand)"
          strokeWidth={2}
          dot={false}
        />
        <Line
          type="monotone"
          dataKey="calls"
          name="API calls"
          stroke="var(--color-muted-foreground)"
          strokeWidth={1.5}
          strokeDasharray="4 3"
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

/**
 * The recharts credits-by-model bar chart, split out so the usage page doesn't
 * statically import recharts. Loaded on demand via `next/dynamic`.
 */
export function CreditsByModelChart({ data }: { data: ByModelPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} margin={{ top: 4, right: 4, bottom: 4, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
        <XAxis
          dataKey="name"
          tick={{ fontSize: 12, fill: "var(--color-muted-foreground)" }}
          stroke="var(--color-border)"
        />
        <YAxis
          tick={{ fontSize: 12, fill: "var(--color-muted-foreground)" }}
          stroke="var(--color-border)"
        />
        <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ fill: "var(--color-muted)" }} />
        <Legend wrapperStyle={LEGEND_STYLE} iconType="square" />
        <Bar dataKey="input" name="Input tokens" fill="var(--color-muted-foreground)" radius={[4, 4, 0, 0]} />
        <Bar dataKey="output" name="Output tokens" fill="var(--color-foreground)" radius={[4, 4, 0, 0]} />
        <Bar dataKey="credits" name="Credits" fill="var(--color-brand)" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
{% endraw %}
