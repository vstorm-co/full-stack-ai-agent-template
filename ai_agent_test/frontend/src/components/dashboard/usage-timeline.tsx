"use client";

import { useEffect, useMemo, useState } from "react";
import { Activity } from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { SegmentedControl } from "@/components/dashboard/segmented-control";
import { EmptyState, ErrorState, LoadingState } from "@/components/states";
import { apiClient, ApiError } from "@/lib/api-client";

interface UsageBucket {
  day: string;
  input_tokens: number;
  output_tokens: number;
  cached_tokens: number;
  credits_charged: number;
  total_calls: number;
}

interface UsageTimelineRead {
  buckets: UsageBucket[];
  days: number;
}

const RANGES = [
  { label: "7d", days: 7 },
  { label: "30d", days: 30 },
  { label: "90d", days: 90 },
] as const;

type Metric = "credits" | "calls" | "tokens";

const METRIC_LABELS: Record<Metric, string> = {
  credits: "Credits",
  calls: "Calls",
  tokens: "Tokens",
};

export function UsageTimeline() {
  const [days, setDays] = useState<number>(30);
  const [metric, setMetric] = useState<Metric>("credits");
  const [data, setData] = useState<UsageBucket[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchTimeline = useMemo(
    () => async (range: number) => {
      setLoading(true);
      setError(null);
      try {
        const res = await apiClient.get<UsageTimelineRead>(
          `/billing/me/credits/usage/timeline?days=${range}`,
        );
        setData(res.buckets);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          setData([]);
        } else {
          setError(err instanceof Error ? err.message : "Failed to load usage timeline");
        }
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    fetchTimeline(days);
  }, [days, fetchTimeline]);

  const chartData = useMemo(() => {
    if (!data) return [];
    return data.map((b) => ({
      day: b.day,
      label: formatDayLabel(b.day, days),
      credits: b.credits_charged,
      calls: b.total_calls,
      tokens: b.input_tokens + b.output_tokens,
    }));
  }, [data, days]);

  const totalForMetric = chartData.reduce((sum, p) => sum + (p[metric] as number), 0);

  return (
    <div className="border-border bg-card flex flex-col rounded-2xl border p-5 lg:p-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">
            Usage over time
          </p>
          <div className="mt-1 flex items-baseline gap-2">
            <span className="font-display text-foreground text-2xl font-bold">
              {totalForMetric.toLocaleString()}
            </span>
            <span className="text-foreground/55 text-sm">
              {METRIC_LABELS[metric].toLowerCase()}
            </span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <SegmentedControl
            value={metric}
            onChange={(v) => setMetric(v as Metric)}
            options={[
              { label: "Credits", value: "credits" },
              { label: "Calls", value: "calls" },
              { label: "Tokens", value: "tokens" },
            ]}
          />
          <SegmentedControl
            value={String(days)}
            onChange={(v) => setDays(Number(v))}
            options={RANGES.map((r) => ({ label: r.label, value: String(r.days) }))}
          />
        </div>
      </div>

      <div className="mt-5 h-56 w-full">
        {loading ? (
          <LoadingState variant="dot-pulse" label="Loading usage…" />
        ) : error ? (
          <ErrorState
            title="Couldn't load usage"
            description={error}
            cta={{ label: "Retry", onClick: () => fetchTimeline(days) }}
            className="h-full"
          />
        ) : !chartData || chartData.length === 0 ? (
          <EmptyState
            icon={Activity}
            title="No usage yet"
            description="Once you start sending messages, usage will appear here."
            fill
          />
        ) : (
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
        )}
      </div>
    </div>
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
  metric: Metric;
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

function formatDayLabel(day: string, _range: number): string {
  const d = new Date(day);
  if (Number.isNaN(d.getTime())) return day;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}
