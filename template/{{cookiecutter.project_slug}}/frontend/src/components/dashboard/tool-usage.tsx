{% raw %}"use client";

import { useEffect, useState } from "react";
import { Wrench } from "lucide-react";

import { LoadingState } from "@/components/states";
import { apiClient } from "@/lib/api-client";
import { cn } from "@/lib/utils";

interface ToolStat {
  tool_name: string;
  total_calls: number;
  failed_calls: number;
  avg_duration_ms: number | null;
  last_used_at: string | null;
}

interface ToolStatsResponse {
  items: ToolStat[];
  days: number;
}

const MAX_ROWS = 6;

function humanize(name: string): string {
  return name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatDuration(ms: number | null): string {
  if (ms === null) return "—";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function ToolUsage() {
  const [data, setData] = useState<ToolStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    apiClient
      .get<ToolStatsResponse>("/conversations/tool-stats?days=7")
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

  const items = (data?.items ?? []).slice(0, MAX_ROWS);
  const maxCalls = items[0]?.total_calls ?? 0;

  return (
    <section className="border-border bg-card flex flex-col rounded-xl border p-5 lg:p-6">
      <header>
        <p className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">
          Tools used · 7d
        </p>
        <h2 className="font-display text-foreground mt-1 text-xl font-semibold tracking-tight">
          What the agent reaches for
        </h2>
      </header>

      <div className="mt-5">
        {loading ? (
          <LoadingState variant="skeleton-list" rows={3} />
        ) : error || items.length === 0 ? (
          <div className="border-foreground/10 flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed py-10 text-center">
            <Wrench className="text-foreground/30 h-8 w-8" />
            <p className="text-foreground/55 text-sm">No tool calls in the last 7 days.</p>
            <p className="text-foreground/45 text-xs">
              Web search, RAG search, etc. show up here once the agent uses them.
            </p>
          </div>
        ) : (
          <ul className="space-y-2">
            {items.map((tool) => {
              const widthPct = maxCalls > 0 ? (tool.total_calls / maxCalls) * 100 : 0;
              const failRate =
                tool.total_calls > 0 ? (tool.failed_calls / tool.total_calls) * 100 : 0;
              const hasFailures = tool.failed_calls > 0;
              return (
                <li
                  key={tool.tool_name}
                  className="border-border/60 bg-background/60 relative overflow-hidden rounded-xl border p-3"
                >
                  <div
                    aria-hidden
                    className="bg-foreground/6 pointer-events-none absolute inset-y-0 left-0"
                    style={{ width: `${Math.max(widthPct, 2)}%` }}
                  />
                  <div className="relative flex items-center gap-3">
                    <Wrench className="text-foreground/55 h-4 w-4 shrink-0" />
                    <div className="min-w-0 flex-1">
                      <p className="text-foreground truncate text-sm font-medium">
                        {humanize(tool.tool_name)}
                      </p>
                      <p className="text-foreground/55 text-xs tabular-nums">
                        avg {formatDuration(tool.avg_duration_ms)}
                        {hasFailures && (
                          <>
                            {" · "}
                            <span className="text-destructive">
                              {tool.failed_calls} fail{tool.failed_calls === 1 ? "" : "s"}
                              {failRate >= 1 ? ` (${failRate.toFixed(0)}%)` : ""}
                            </span>
                          </>
                        )}
                      </p>
                    </div>
                    <div className="text-right">
                      <p
                        className={cn(
                          "font-mono text-sm tabular-nums",
                          hasFailures ? "text-foreground" : "text-foreground",
                        )}
                      >
                        {tool.total_calls.toLocaleString()}
                      </p>
                      <p className="text-foreground/45 text-[10px] tracking-wider uppercase">
                        call{tool.total_calls === 1 ? "" : "s"}
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
