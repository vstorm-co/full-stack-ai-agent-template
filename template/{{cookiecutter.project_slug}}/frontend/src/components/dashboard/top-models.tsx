{% raw %}"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowUpRight, Cpu } from "lucide-react";

import { LoadingState } from "@/components/states";
import { apiClient } from "@/lib/api-client";
import { ROUTES } from "@/lib/constants";
import { cn } from "@/lib/utils";

interface ByModel {
  model: string;
  provider: string;
  input_tokens: number;
  output_tokens: number;
  cached_tokens: number;
  credits_charged: number;
  total_calls: number;
}

interface UsageAggregate {
  total_credits_charged: number;
  total_calls: number;
  by_model: ByModel[];
}

// Stronger background opacity (35% vs 15%) so the provider chip stays readable
// on top of the per-row credit-share progress fill. The text uses the deepest
// available shade in light mode and a lighter shade only in dark mode.
const PROVIDER_TONE: Record<string, string> = {
  openai: "bg-emerald-500/35 text-emerald-900 dark:text-emerald-200",
  anthropic: "bg-amber-500/35 text-amber-900 dark:text-amber-200",
  google: "bg-blue-500/35 text-blue-900 dark:text-blue-200",
  unknown: "bg-foreground/15 text-foreground",
};

const MAX_ROWS = 5;

export function TopModels() {
  const [data, setData] = useState<UsageAggregate | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    apiClient
      .get<UsageAggregate>("/billing/me/credits/usage?days=7")
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const top = (data?.by_model ?? []).slice(0, MAX_ROWS);
  const totalCredits = data?.total_credits_charged ?? 0;

  return (
    <section className="border-border bg-card flex flex-col rounded-xl border p-5 lg:p-6">
      <header className="flex items-end justify-between gap-3">
        <div>
          <p className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">
            Top models · 7d
          </p>
          <h2 className="font-display text-foreground mt-1 text-xl font-semibold tracking-tight">
            Where credits go
          </h2>
        </div>
        <Link
          href={ROUTES.BILLING_USAGE}
          className="text-foreground/55 hover:text-foreground inline-flex items-center gap-1 text-xs font-medium transition-colors"
        >
          Full breakdown
          <ArrowUpRight className="h-3 w-3" />
        </Link>
      </header>

      <div className="mt-5">
        {loading ? (
          <LoadingState variant="skeleton-list" rows={3} />
        ) : error || top.length === 0 ? (
          <div className="border-foreground/10 bg-card flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed py-10 text-center">
            <Cpu className="text-foreground/30 h-8 w-8" />
            <p className="text-foreground/55 text-sm">No model usage in the last 7 days.</p>
            <p className="text-foreground/45 text-xs">
              Send a chat message to start tracking model spend.
            </p>
          </div>
        ) : (
          <ul className="space-y-2">
            {top.map((m) => {
              const pct = totalCredits > 0 ? (m.credits_charged / totalCredits) * 100 : 0;
              const tokens = m.input_tokens + m.output_tokens;
              return (
                <li
                  key={`${m.provider}:${m.model}`}
                  className="border-border/60 bg-background/60 relative overflow-hidden rounded-xl border p-3"
                >
                  <div
                    aria-hidden
                    className="bg-foreground/6 pointer-events-none absolute inset-y-0 left-0"
                    style={{ width: `${Math.max(pct, 2)}%` }}
                  />
                  <div className="relative flex items-center gap-3">
                    <span
                      className={cn(
                        "shrink-0 rounded-full px-2 py-0.5 font-mono text-[10px] tracking-wider uppercase",
                        PROVIDER_TONE[m.provider] ?? PROVIDER_TONE.unknown,
                      )}
                    >
                      {m.provider}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-foreground truncate text-sm font-medium">{m.model}</p>
                      <p className="text-foreground/55 text-xs tabular-nums">
                        {tokens.toLocaleString()} tokens · {m.total_calls.toLocaleString()} call
                        {m.total_calls === 1 ? "" : "s"}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-foreground font-mono text-sm tabular-nums">
                        {m.credits_charged.toLocaleString()}
                      </p>
                      <p className="text-foreground/45 text-[10px] tabular-nums">
                        {pct < 1 ? "<1" : pct.toFixed(0)}%
                      </p>
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </section>
  );
}
{% endraw %}
