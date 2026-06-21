{% raw %}"use client";

import { useCallback, useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { Activity, Coins, Cpu, Download } from "lucide-react";

import { StatCard } from "@/components/dashboard/stat-card";
import { LoadingState } from "@/components/states";
import { Button } from "@/components/ui";
import { apiClient } from "@/lib/api-client";

// Recharts charts load on demand so the usage page's initial bundle stays light.
const CHART_FALLBACK = <div className="bg-foreground/5 h-full w-full animate-pulse rounded-md" />;
const DailyCreditsChart = dynamic(
  () => import("./usage-charts").then((m) => m.DailyCreditsChart),
  { ssr: false, loading: () => <div className="h-[240px]">{CHART_FALLBACK}</div> },
);
const CreditsByModelChart = dynamic(
  () => import("./usage-charts").then((m) => m.CreditsByModelChart),
  { ssr: false, loading: () => <div className="h-[280px]">{CHART_FALLBACK}</div> },
);

interface UsageAggregate {
  total_input_tokens: number;
  total_output_tokens: number;
  total_cached_tokens: number;
  total_credits_charged: number;
  total_calls: number;
  by_model: Array<{
    model: string;
    provider: string;
    input_tokens: number;
    output_tokens: number;
    credits_charged: number;
    total_calls: number;
  }>;
}

interface UsageDailyBucket {
  day: string;
  input_tokens: number;
  output_tokens: number;
  cached_tokens: number;
  credits_charged: number;
  total_calls: number;
}

interface UsageTimeline {
  buckets: UsageDailyBucket[];
  days: number;
}

interface CreditTransaction {
  id: string;
  delta: number;
  balance_after: number;
  type: string;
  description: string | null;
  created_at: string;
}

function ChartCard({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="border-border bg-card rounded-xl border p-5">
      <header className="mb-4">
        <h2 className="text-foreground text-sm font-semibold">{title}</h2>
        {description && <p className="text-muted-foreground mt-0.5 text-xs">{description}</p>}
      </header>
      {children}
    </section>
  );
}

export default function UsageDashboardPage() {
  const [aggregate, setAggregate] = useState<UsageAggregate | null>(null);
  const [timeline, setTimeline] = useState<UsageTimeline | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [agg, tl] = await Promise.all([
        apiClient.get<UsageAggregate>("/billing/me/credits/usage"),
        apiClient.get<UsageTimeline>("/billing/me/credits/usage/timeline?days=30"),
      ]);
      setAggregate(agg);
      setTimeline(tl);
    } catch {
      setAggregate(null);
      setTimeline(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleExport = async () => {
    try {
      const txData = await apiClient.get<{ items: CreditTransaction[] }>(
        "/billing/me/credits/transactions?skip=0&limit=1000",
      );
      const csv = [
        "Date,Type,Delta,Balance After,Description",
        ...txData.items.map((t) =>
          [
            new Date(t.created_at).toISOString(),
            t.type,
            t.delta,
            t.balance_after,
            `"${(t.description ?? "").replace(/"/g, '""')}"`,
          ].join(","),
        ),
      ].join("\n");
      const blob = new Blob([csv], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "credits-export.csv";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      /* ignore */
    }
  };

  const byModelChartData =
    aggregate?.by_model.map((m) => ({
      name: m.model.split("-").slice(-2).join("-"),
      input: m.input_tokens,
      output: m.output_tokens,
      credits: m.credits_charged,
    })) ?? [];

  const timelineChartData =
    timeline?.buckets.map((b) => ({
      day: b.day.slice(5), // "MM-DD"
      credits: b.credits_charged,
      calls: b.total_calls,
    })) ?? [];

  const totalTokens = aggregate
    ? aggregate.total_input_tokens + aggregate.total_output_tokens
    : null;

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <Button type="button" variant="outline" size="sm" onClick={handleExport}>
          <Download className="h-3.5 w-3.5" />
          Export CSV
        </Button>
      </div>

      {isLoading ? (
        <LoadingState variant="stats" rows={3} />
      ) : (
        <div className="grid gap-4 sm:grid-cols-3">
          <StatCard
            label="Credits used"
            value={aggregate?.total_credits_charged.toLocaleString() ?? "—"}
            icon={Coins}
          />
          <StatCard label="Tokens" value={totalTokens?.toLocaleString() ?? "—"} icon={Cpu} />
          <StatCard
            label="API calls"
            value={aggregate?.total_calls.toLocaleString() ?? "—"}
            icon={Activity}
          />
        </div>
      )}

      {!isLoading && timelineChartData.length > 0 && (
        <ChartCard
          title="Daily usage"
          description="Last 30 days of credit consumption and API calls."
        >
          <DailyCreditsChart data={timelineChartData} />
        </ChartCard>
      )}

      {!isLoading && byModelChartData.length > 0 && (
        <ChartCard
          title="Usage by model"
          description="Tokens and credits, by model."
        >
          <CreditsByModelChart data={byModelChartData} />
        </ChartCard>
      )}

      {!isLoading && aggregate && aggregate.by_model.length > 0 && (
        <ChartCard title="Per-model breakdown">
          <div className="divide-border -mx-1 divide-y">
            {aggregate.by_model.map((m) => (
              <div key={m.model} className="grid grid-cols-4 gap-4 px-1 py-3 text-sm tabular-nums">
                <div className="col-span-2 min-w-0">
                  <p className="text-foreground truncate font-medium">{m.model}</p>
                  <p className="text-muted-foreground text-xs">{m.provider}</p>
                </div>
                <div>
                  <p className="text-muted-foreground text-xs">Tokens</p>
                  <p className="text-foreground font-mono">
                    {(m.input_tokens + m.output_tokens).toLocaleString()}
                  </p>
                </div>
                <div>
                  <p className="text-muted-foreground text-xs">Credits</p>
                  <p className="text-foreground font-mono">{m.credits_charged.toLocaleString()}</p>
                </div>
              </div>
            ))}
          </div>
        </ChartCard>
      )}
    </div>
  );
}
{% endraw %}
