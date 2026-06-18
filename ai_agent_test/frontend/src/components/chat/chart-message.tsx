"use client";

import { memo, useMemo } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { ChartSpec } from "@/types";

// Neutral, brand-leaning defaults. The agent can override per-series colors
// or the whole palette via spec.style.palette.
const DEFAULT_PALETTE = [
  "#6366f1",
  "#10b981",
  "#f59e0b",
  "#ef4444",
  "#8b5cf6",
  "#06b6d4",
  "#ec4899",
  "#84cc16",
];

// Recharts renders raw SVG, so it can't use Tailwind classes — it must read
// the app's CSS theme variables inline. These resolve to the right values in
// both light and dark mode automatically.
const AXIS_TICK = { fill: "var(--color-muted-foreground)", fontSize: 11 } as const;
const AXIS_LINE = { stroke: "var(--color-border)" } as const;
const GRID_STROKE = "var(--color-border)";

const TOOLTIP_CONTENT = {
  background: "var(--color-popover)",
  border: "1px solid var(--color-border)",
  borderRadius: 10,
  fontSize: 12,
  padding: "8px 10px",
  boxShadow: "0 8px 24px rgb(0 0 0 / 0.16)",
} as const;
const TOOLTIP_LABEL = {
  color: "var(--color-muted-foreground)",
  marginBottom: 4,
  fontSize: 11,
  fontWeight: 600,
} as const;
const TOOLTIP_ITEM = { color: "var(--color-popover-foreground)" } as const;
const LEGEND_STYLE = { fontSize: 12, paddingTop: 6 } as const;

const LINE_CURSOR = {
  stroke: "var(--color-muted-foreground)",
  strokeOpacity: 0.4,
  strokeDasharray: "3 3",
} as const;
const BAR_CURSOR = { fill: "var(--color-muted)", fillOpacity: 0.5 } as const;

/** Compact axis numbers: 60000 → 60k, 1_500_000 → 1.5M. Tooltip keeps the
 *  exact value; only the axis ticks are abbreviated to stop them colliding. */
function compact(value: unknown): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return String(value);
  const abs = Math.abs(value);
  if (abs >= 1e9) return `${(value / 1e9).toFixed(1).replace(/\.0$/, "")}B`;
  if (abs >= 1e6) return `${(value / 1e6).toFixed(1).replace(/\.0$/, "")}M`;
  if (abs >= 1e3) return `${(value / 1e3).toFixed(1).replace(/\.0$/, "")}k`;
  return String(value);
}

/** Parse a `create_chart` tool result into a ChartSpec, or null if it isn't one. */
export function parseChartResult(result: unknown): ChartSpec | null {
  let payload: unknown = result;
  if (typeof result === "string") {
    try {
      payload = JSON.parse(result);
    } catch {
      return null;
    }
  }
  if (payload && typeof payload === "object" && (payload as { kind?: unknown }).kind === "chart") {
    return payload as ChartSpec;
  }
  return null;
}

/**
 * Memoized so it only re-renders when the chart `spec` actually changes. During
 * streaming, MessageItem re-renders on every text/thinking delta — without
 * memoization, Recharts' ResponsiveContainer + ResizeObserver fire on each one
 * and can momentarily report container size as -1 mid-layout. That triggers a
 * `setState` inside Recharts' internal `RenderedTicksReporter` which feeds
 * back into the store-subscribed re-render chain → infinite update loop.
 */
export const ChartMessage = memo(ChartMessageInner);

function ChartMessageInner({ spec }: { spec: ChartSpec }) {
  const palette = useMemo(
    () =>
      spec.style?.palette && spec.style.palette.length > 0 ? spec.style.palette : DEFAULT_PALETTE,
    [spec.style],
  );

  const colorFor = (index: number, override?: string | null) =>
    override || palette[index % palette.length];

  const showGrid = spec.style?.grid !== false;
  const showLegend = spec.style?.legend !== false;
  const stacked = spec.style?.stacked === true;
  const xLabel = spec.style?.x_label ?? undefined;
  const yLabel = spec.style?.y_label ?? undefined;

  const margin = { top: 12, right: 18, bottom: xLabel ? 22 : 6, left: yLabel ? 12 : 0 };

  const xAxis = (
    <XAxis
      dataKey={spec.x_key}
      tick={AXIS_TICK}
      tickLine={false}
      axisLine={AXIS_LINE}
      tickMargin={8}
      label={
        xLabel
          ? {
              value: xLabel,
              position: "insideBottom",
              offset: -10,
              fill: "var(--color-muted-foreground)",
              fontSize: 11,
            }
          : undefined
      }
    />
  );

  const yAxis = (
    <YAxis
      tick={AXIS_TICK}
      tickLine={false}
      axisLine={AXIS_LINE}
      tickFormatter={compact}
      width={48}
      label={
        yLabel
          ? {
              value: yLabel,
              angle: -90,
              position: "insideLeft",
              offset: 4,
              style: {
                textAnchor: "middle",
                fill: "var(--color-muted-foreground)",
                fontSize: 11,
              },
            }
          : undefined
      }
    />
  );

  const grid = showGrid ? (
    <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} vertical={false} />
  ) : null;

  const tooltip = (cursor: object) => (
    <Tooltip
      contentStyle={TOOLTIP_CONTENT}
      labelStyle={TOOLTIP_LABEL}
      itemStyle={TOOLTIP_ITEM}
      cursor={cursor}
    />
  );

  const legend = showLegend ? (
    <Legend wrapperStyle={LEGEND_STYLE} iconType="circle" iconSize={9} />
  ) : null;

  const renderChart = () => {
    switch (spec.chart_type) {
      case "bar":
        return (
          <BarChart data={spec.data} margin={margin}>
            {grid}
            {xAxis}
            {yAxis}
            {tooltip(BAR_CURSOR)}
            {legend}
            {spec.series.map((s, i) => (
              <Bar
                key={s.key}
                dataKey={s.key}
                name={s.label ?? s.key}
                fill={colorFor(i, s.color)}
                stackId={stacked ? "stack" : undefined}
                radius={[4, 4, 0, 0]}
                maxBarSize={56}
              />
            ))}
          </BarChart>
        );
      case "area":
        return (
          <AreaChart data={spec.data} margin={margin}>
            <defs>
              {spec.series.map((s, i) => (
                <linearGradient key={s.key} id={`area-${i}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={colorFor(i, s.color)} stopOpacity={0.35} />
                  <stop offset="95%" stopColor={colorFor(i, s.color)} stopOpacity={0.02} />
                </linearGradient>
              ))}
            </defs>
            {grid}
            {xAxis}
            {yAxis}
            {tooltip(LINE_CURSOR)}
            {legend}
            {spec.series.map((s, i) => (
              <Area
                key={s.key}
                type="monotone"
                dataKey={s.key}
                name={s.label ?? s.key}
                stroke={colorFor(i, s.color)}
                strokeWidth={2}
                fill={`url(#area-${i})`}
                stackId={stacked ? "stack" : undefined}
              />
            ))}
          </AreaChart>
        );
      case "pie": {
        const valueKey = spec.series[0]?.key ?? "value";
        return (
          <PieChart>
            {tooltip({})}
            {legend}
            <Pie
              data={spec.data}
              dataKey={valueKey}
              nameKey={spec.x_key}
              cx="50%"
              cy="50%"
              innerRadius="56%"
              outerRadius="82%"
              paddingAngle={2}
              stroke="var(--color-background)"
              strokeWidth={2}
            >
              {spec.data.map((_, i) => (
                <Cell key={i} fill={colorFor(i)} />
              ))}
            </Pie>
          </PieChart>
        );
      }
      case "scatter":
        return (
          <ScatterChart margin={margin}>
            {showGrid && <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} />}
            {xAxis}
            {yAxis}
            {tooltip(LINE_CURSOR)}
            {legend}
            {spec.series.map((s, i) => (
              <Scatter
                key={s.key}
                data={spec.data}
                dataKey={s.key}
                name={s.label ?? s.key}
                fill={colorFor(i, s.color)}
              />
            ))}
          </ScatterChart>
        );
      case "line":
      default:
        return (
          <LineChart data={spec.data} margin={margin}>
            {grid}
            {xAxis}
            {yAxis}
            {tooltip(LINE_CURSOR)}
            {legend}
            {spec.series.map((s, i) => (
              <Line
                key={s.key}
                type="monotone"
                dataKey={s.key}
                name={s.label ?? s.key}
                stroke={colorFor(i, s.color)}
                dot={false}
                activeDot={{ r: 4 }}
                strokeWidth={2}
              />
            ))}
          </LineChart>
        );
    }
  };

  return (
    <div className="bg-card overflow-hidden rounded-xl border p-3 sm:p-4">
      <p className="text-foreground mb-3 text-sm font-semibold">{spec.title}</p>
      <div className="h-[300px] w-full" style={{ minWidth: 1, minHeight: 1 }}>
        <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1}>
          {renderChart()}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
