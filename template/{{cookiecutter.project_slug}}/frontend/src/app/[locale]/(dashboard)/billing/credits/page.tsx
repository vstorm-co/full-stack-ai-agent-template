"use client";

import { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  AlertCircle,
  ArrowUpRight,
  Coins,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Wallet,
} from "lucide-react";
import { toast } from "sonner";

import { StatCard } from "@/components/dashboard/stat-card";
import { LoadingState } from "@/components/states";
import { Alert, AlertDescription, AlertTitle, Badge, Button } from "@/components/ui";
import { useBilling, useCredits } from "@/hooks";
import { apiClient } from "@/lib/api-client";
import { ROUTES } from "@/lib/constants";
import { cn } from "@/lib/utils";

// Recharts sparkline loads on demand so the credits page bundle stays light.
const UsageSpark = dynamic(() => import("./usage-spark").then((m) => m.UsageSpark), {
  ssr: false,
  loading: () => <div className="bg-foreground/5 h-full w-full animate-pulse rounded-md" />,
});

interface UsageBucket {
  day: string;
  credits_charged: number;
}

interface UsageTimelineRead {
  buckets: UsageBucket[];
  days: number;
}

function formatDateTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function humanizeType(t: string): string {
  return t.replace(/_/g, " ");
}

export default function CreditsPage() {
  const searchParams = useSearchParams();
  const { balance, transactions, isLoading, txLoading } = useCredits();
  const { startCheckout, isLoading: checkoutLoading } = useBilling();
  const [timeline, setTimeline] = useState<UsageBucket[] | null>(null);

  useEffect(() => {
    if (searchParams.get("topup") === "1") {
      toast.success("Credits added to your account!");
    }
  }, [searchParams]);

  useEffect(() => {
    apiClient
      .get<UsageTimelineRead>("/billing/me/credits/usage/timeline?days=30")
      .then((d) => setTimeline(d.buckets))
      .catch(() => setTimeline([]));
  }, []);

  const last7Total = useMemo(
    () => (timeline ?? []).slice(-7).reduce((a, b) => a + b.credits_charged, 0),
    [timeline],
  );
  const prior7Total = useMemo(
    () => (timeline ?? []).slice(-14, -7).reduce((a, b) => a + b.credits_charged, 0),
    [timeline],
  );
  const trendPct =
    prior7Total > 0 ? ((last7Total - prior7Total) / prior7Total) * 100 : last7Total > 0 ? 100 : 0;

  const sparkData = useMemo(
    () => (timeline ?? []).slice(-30).map((b, i) => ({ i, v: b.credits_charged })),
    [timeline],
  );

  const low = balance && balance.low_threshold > 0 && balance.balance < balance.low_threshold;

  // Projected days of runway from the average daily burn over the timeline window.
  const projection = useMemo(() => {
    if (!balance || !timeline || timeline.length === 0) return null;
    const totalUsed = timeline.reduce((a, b) => a + b.credits_charged, 0);
    const perDay = totalUsed / timeline.length;
    if (perDay <= 0 || balance.balance <= 0) return null;
    const daysLeft = Math.floor(balance.balance / perDay);
    return { perDay, daysLeft };
  }, [balance, timeline]);

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <Button
          onClick={() =>
            startCheckout({
              success_url: window.location.href + "?topup=1",
              cancel_url: window.location.href,
            })
          }
          disabled={checkoutLoading}
          size="sm"
        >
          <Wallet className="h-3.5 w-3.5" />
          {checkoutLoading ? "Opening…" : "Top up"}
        </Button>
      </div>

      {isLoading ? (
        <LoadingState variant="stats" rows={3} />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <StatCard
            label="Current balance"
            value={balance?.balance.toLocaleString() ?? "—"}
            unit="credits"
            icon={Sparkles}
          />
          <StatCard
            label="Used · last 7 days"
            value={last7Total.toLocaleString()}
            unit="credits"
            delta={timeline ? Number(trendPct.toFixed(1)) : undefined}
            deltaLabel="wk-over-wk"
            icon={Coins}
          />
          <StatCard
            label="Low threshold"
            value={balance?.low_threshold ? balance.low_threshold.toLocaleString() : "Off"}
            icon={AlertCircle}
          />
        </div>
      )}

      {low && balance && (
        <Alert variant="warning">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Low credit balance</AlertTitle>
          <AlertDescription>
            Balance is below your alert threshold of{" "}
            {balance.low_threshold.toLocaleString()} credits.
            {projection && (
              <>
                {" "}
                At the current rate (~{Math.round(projection.perDay).toLocaleString()}/day) it will
                run out in about {projection.daysLeft.toLocaleString()}{" "}
                {projection.daysLeft === 1 ? "day" : "days"}.
              </>
            )}{" "}
            Top up to avoid interruptions.
          </AlertDescription>
        </Alert>
      )}

      {!low && projection && projection.daysLeft <= 14 && (
        <Alert variant="default">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Credits running low soon</AlertTitle>
          <AlertDescription>
            At the current rate (~{Math.round(projection.perDay).toLocaleString()}/day) your balance
            will last about {projection.daysLeft.toLocaleString()}{" "}
            {projection.daysLeft === 1 ? "day" : "days"}.
          </AlertDescription>
        </Alert>
      )}

      <section className="border-border bg-card rounded-xl border p-5">
        <div className="flex items-baseline justify-between">
          <h2 className="text-foreground text-sm font-semibold">Usage · last 30 days</h2>
          {timeline && (
            <span
              className={cn(
                "inline-flex items-center gap-1 font-mono text-[11px] font-semibold",
                trendPct > 0
                  ? "text-destructive"
                  : trendPct < 0
                    ? "text-muted-foreground"
                    : "text-muted-foreground",
              )}
            >
              {trendPct > 0 ? (
                <TrendingUp className="h-3 w-3" />
              ) : trendPct < 0 ? (
                <TrendingDown className="h-3 w-3" />
              ) : null}
              {Math.abs(trendPct).toFixed(1)}% wk-over-wk
            </span>
          )}
        </div>
        <div className="mt-4 h-24 w-full">
          {!timeline ? (
            <div className="bg-foreground/5 h-full animate-pulse rounded-md" />
          ) : sparkData.length < 2 ? (
            <p className="text-muted-foreground text-xs">Not enough data yet.</p>
          ) : (
            <UsageSpark data={sparkData} />
          )}
        </div>
      </section>

      <section className="border-border bg-card rounded-xl border">
        <div className="border-border flex items-center justify-between border-b px-5 py-4">
          <div>
            <h2 className="text-foreground text-sm font-semibold">Transaction history</h2>
            <p className="text-muted-foreground text-xs">
              All credit grants, top-ups, and consumption events.
            </p>
          </div>
          {transactions && transactions.total > (transactions.items.length ?? 0) && (
            <span className="text-muted-foreground font-mono text-[11px] tracking-wider uppercase">
              {transactions.items.length} / {transactions.total}
            </span>
          )}
        </div>

        {txLoading ? (
          <div className="p-5">
            <LoadingState variant="skeleton-list" rows={4} />
          </div>
        ) : !transactions || transactions.items.length === 0 ? (
          <div className="px-5 py-12 text-center">
            <Coins className="text-muted-foreground mx-auto h-7 w-7" />
            <p className="text-foreground mt-3 text-sm">No transactions yet</p>
            <p className="text-muted-foreground mt-1 text-xs">
              Activity will show here once you start using AI features.
            </p>
          </div>
        ) : (
          <ul className="divide-border divide-y">
            {transactions.items.map((tx) => (
              <li
                key={tx.id}
                className="flex flex-wrap items-center justify-between gap-3 px-5 py-3.5"
              >
                <div className="min-w-0 flex-1">
                  <p className="text-foreground text-sm font-medium">
                    {tx.description ?? "Credit transaction"}
                  </p>
                  <div className="text-muted-foreground mt-1 flex flex-wrap items-center gap-2 text-xs">
                    <Badge variant="outline" className="font-mono text-[10px] uppercase">
                      {humanizeType(tx.type)}
                    </Badge>
                    <span>{formatDateTime(tx.created_at)}</span>
                  </div>
                </div>
                <div className="text-right">
                  <p
                    className={cn(
                      "font-mono text-sm font-semibold tabular-nums",
                      tx.delta > 0 ? "text-foreground" : "text-muted-foreground",
                    )}
                  >
                    {tx.delta > 0 ? "+" : ""}
                    {tx.delta.toLocaleString()}
                  </p>
                  <p className="text-muted-foreground mt-0.5 font-mono text-[10px] tracking-wider uppercase">
                    bal {tx.balance_after.toLocaleString()}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <p className="text-muted-foreground inline-flex items-center gap-1.5 text-xs">
        Need a custom credit pack?{" "}
        <Link
          href={ROUTES.CONTACT}
          className="text-foreground hover:text-foreground/80 inline-flex items-center gap-1 font-medium underline-offset-4 hover:underline"
        >
          Contact us
          <ArrowUpRight className="h-3 w-3" />
        </Link>
      </p>
    </div>
  );
}
