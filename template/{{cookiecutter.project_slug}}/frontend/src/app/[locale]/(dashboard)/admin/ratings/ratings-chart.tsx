{% raw %}"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

interface RatingDayPoint {
  date: string;
  likes: number;
  dislikes: number;
}

/**
 * Ratings-per-day bar chart. Split out so the ratings page doesn't statically
 * import recharts — loaded on demand via `next/dynamic`.
 */
export function RatingsChart({ data }: { data: RatingDayPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 0 }} barGap={2}>
        <CartesianGrid
          strokeDasharray="3 3"
          stroke="oklch(from var(--color-foreground) l c h / 0.07)"
          vertical={false}
        />
        <XAxis
          dataKey="date"
          stroke="oklch(from var(--color-foreground) l c h / 0.3)"
          fontSize={11}
          tickLine={false}
          axisLine={false}
          tick={{
            fontFamily: "var(--font-mono)",
            fill: "oklch(from var(--color-foreground) l c h / 0.45)",
          }}
        />
        <YAxis
          stroke="oklch(from var(--color-foreground) l c h / 0.3)"
          fontSize={11}
          tickLine={false}
          axisLine={false}
          tick={{
            fontFamily: "var(--font-mono)",
            fill: "oklch(from var(--color-foreground) l c h / 0.45)",
          }}
          width={28}
          allowDecimals={false}
        />
        <Tooltip
          content={<RatingsTooltip />}
          cursor={{ fill: "oklch(from var(--color-foreground) l c h / 0.04)" }}
        />
        <Bar
          dataKey="likes"
          name="Likes"
          fill="oklch(from var(--color-foreground) l c h / 0.75)"
          radius={[3, 3, 0, 0]}
          maxBarSize={24}
        />
        <Bar
          dataKey="dislikes"
          name="Dislikes"
          fill="oklch(from var(--color-foreground) l c h / 0.3)"
          radius={[3, 3, 0, 0]}
          maxBarSize={24}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}

function RatingsTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="border-border bg-card rounded-xl border px-3 py-2.5 text-xs shadow-lg">
      <p className="text-muted-foreground mb-2 font-mono text-[10px] tracking-wider uppercase">
        {label}
      </p>
      {payload.map((p) => (
        <div key={p.name} className="flex items-center gap-2">
          <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: p.color }} />
          <span className="text-muted-foreground">{p.name}</span>
          <span className="text-foreground ml-3 font-semibold tabular-nums">{p.value}</span>
        </div>
      ))}
    </div>
  );
}
{% endraw %}
