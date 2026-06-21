{% raw %}"use client";

import dynamic from "next/dynamic";

import type { ChartSpec } from "@/types";

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
 * Recharts is a large dependency. It's only needed when an assistant message
 * actually contains a `create_chart` tool result, so the chart renderer lives in
 * `chart-message.impl.tsx` and is loaded on demand via `next/dynamic`. This keeps
 * recharts out of the initial chat bundle. `parseChartResult` stays a static,
 * synchronous export so callers can decide whether to render a chart without
 * pulling in recharts.
 *
 * `ssr: false` because Recharts' ResponsiveContainer measures the DOM. The
 * placeholder matches the chart card's height to avoid layout shift.
 */
export const ChartMessage = dynamic(
  () => import("./chart-message.impl").then((m) => m.ChartMessage),
  {
    ssr: false,
    loading: () => (
      <div className="bg-card overflow-hidden rounded-xl border p-3 sm:p-4">
        <div className="bg-foreground/10 mb-3 h-4 w-32 animate-pulse rounded" />
        <div className="bg-foreground/5 h-[300px] w-full animate-pulse rounded-md" />
      </div>
    ),
  },
);
{% endraw %}
