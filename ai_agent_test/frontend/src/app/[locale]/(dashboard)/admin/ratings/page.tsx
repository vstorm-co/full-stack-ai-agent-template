"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  Download,
  ExternalLink,
  MessageSquare,
  ThumbsDown,
  ThumbsUp,
  TrendingUp,
} from "lucide-react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { apiClient } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import type { MessageRatingListResponse, RatingSummary } from "@/types";

const PAGE_SIZE = 50;
type RatingFilter = "all" | "positive" | "negative";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function AdminRatingsPage() {
  const [summary, setSummary] = useState<RatingSummary | null>(null);
  const [ratings, setRatings] = useState<MessageRatingListResponse | null>(null);
  const [filter, setFilter] = useState<RatingFilter>("all");
  const [commentsOnly, setCommentsOnly] = useState(false);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [exportFormat, setExportFormat] = useState<"json" | "csv">("csv");

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const ratingsParams = new URLSearchParams({
        skip: String(page * PAGE_SIZE),
        limit: String(PAGE_SIZE),
        with_comments_only: String(commentsOnly),
      });
      if (filter !== "all") {
        ratingsParams.set("rating_filter", filter === "positive" ? "1" : "-1");
      }
      const [summaryData, ratingsData] = await Promise.all([
        apiClient.get<RatingSummary>("/admin/ratings/summary?days=30"),
        apiClient.get<MessageRatingListResponse>(`/admin/ratings?${ratingsParams}`),
      ]);
      setSummary(summaryData);
      setRatings(ratingsData);
    } catch {
      /* ignore — empty state handles errors */
    } finally {
      setLoading(false);
    }
  }, [page, filter, commentsOnly]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleExport = () => {
    const params = new URLSearchParams({ export_format: exportFormat });
    if (filter !== "all") params.set("rating_filter", filter === "positive" ? "1" : "-1");
    if (commentsOnly) params.set("with_comments_only", "true");
    window.open(`/api/admin/ratings/export?${params}`, "_blank");
  };

  const totalPages = ratings ? Math.ceil(ratings.total / PAGE_SIZE) : 0;
  const approvalRate =
    summary && summary.total_ratings > 0
      ? Math.round((summary.like_count / summary.total_ratings) * 100)
      : null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">
            Response ratings
          </p>
          <h2 className="font-display text-foreground [&_em]:font-accent mt-1 text-xl font-semibold tracking-tight [&_em]:font-normal [&_em]:italic">
            Message <em>quality.</em>
          </h2>
          <p className="text-foreground/65 mt-1 text-sm">
            User feedback on AI responses — last 30 days.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={exportFormat} onValueChange={(v) => setExportFormat(v as "json" | "csv")}>
            <SelectTrigger className="rounded-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="csv">CSV</SelectItem>
              <SelectItem value="json">JSON</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" onClick={handleExport} className="rounded-full">
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>
        </div>
      </header>

      {/* Stat tiles */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile
          label="Total ratings"
          value={loading ? null : String(summary?.total_ratings ?? 0)}
        />
        <StatTile
          label="Likes"
          value={loading ? null : String(summary?.like_count ?? 0)}
          accent="green"
          icon={<ThumbsUp className="h-4 w-4" />}
        />
        <StatTile
          label="Dislikes"
          value={loading ? null : String(summary?.dislike_count ?? 0)}
          accent="red"
          icon={<ThumbsDown className="h-4 w-4" />}
        />
        <StatTile
          label="Approval rate"
          value={loading ? null : approvalRate !== null ? `${approvalRate}%` : "—"}
          icon={<TrendingUp className="h-4 w-4" />}
        />
      </div>

      {/* Chart */}
      {!loading && summary && summary.ratings_by_day.length > 0 && (
        <section className="border-foreground/10 bg-card rounded-2xl border p-6">
          <p className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">
            Over time
          </p>
          <h2 className="font-display text-foreground mt-1 text-base font-semibold tracking-tight">
            Ratings per day
          </h2>
          <div className="mt-5 h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={summary.ratings_by_day}
                margin={{ top: 4, right: 4, bottom: 0, left: 0 }}
                barGap={2}
              >
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
                  fill="#22c55e"
                  radius={[3, 3, 0, 0]}
                  maxBarSize={24}
                />
                <Bar
                  dataKey="dislikes"
                  name="Dislikes"
                  fill="#ef4444"
                  radius={[3, 3, 0, 0]}
                  maxBarSize={24}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-3 flex items-center gap-5">
            <span className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-green-500" />
              <span className="text-foreground/55 font-mono text-[10px] tracking-wider uppercase">
                Likes
              </span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-red-500" />
              <span className="text-foreground/55 font-mono text-[10px] tracking-wider uppercase">
                Dislikes
              </span>
            </span>
          </div>
        </section>
      )}

      {/* Filters + table */}
      <section className="border-foreground/10 bg-card rounded-2xl border">
        <div className="border-foreground/10 flex flex-wrap items-center justify-between gap-3 border-b px-5 py-4">
          <div className="flex items-center gap-3">
            <Select
              value={filter}
              onValueChange={(v) => {
                setFilter(v as RatingFilter);
                setPage(0);
              }}
            >
              <SelectTrigger className="w-36 rounded-full text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All ratings</SelectItem>
                <SelectItem value="positive">Likes only</SelectItem>
                <SelectItem value="negative">Dislikes only</SelectItem>
              </SelectContent>
            </Select>
            <label className="flex cursor-pointer items-center gap-2 text-xs">
              <Checkbox
                checked={commentsOnly}
                onCheckedChange={(v) => {
                  setCommentsOnly(!!v);
                  setPage(0);
                }}
              />
              <span className="text-foreground/65">With comments only</span>
            </label>
          </div>
          {ratings && !loading && (
            <span className="text-foreground/45 font-mono text-[11px] tracking-wider uppercase">
              {ratings.total.toLocaleString()} result{ratings.total === 1 ? "" : "s"}
            </span>
          )}
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-foreground/[0.07] border-b">
                {["Date", "Rating", "Comment", "Message", "User", ""].map((h, i) => (
                  <th
                    key={i}
                    className="text-foreground/40 px-5 py-3 text-left font-mono text-[10px] tracking-wider uppercase"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-foreground/[0.05] divide-y">
              {loading ? (
                Array.from({ length: 8 }).map((_, i) => (
                  <tr key={i}>
                    <td colSpan={6} className="px-5 py-3">
                      <div className="bg-foreground/[0.05] h-5 w-full animate-pulse rounded" />
                    </td>
                  </tr>
                ))
              ) : ratings?.items.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-16 text-center">
                    <MessageSquare className="text-foreground/20 mx-auto mb-3 h-8 w-8" />
                    <p className="text-foreground/45 text-sm">No ratings found.</p>
                    <p className="text-foreground/35 mt-1 text-xs">
                      Try adjusting the filters above.
                    </p>
                  </td>
                </tr>
              ) : (
                ratings?.items.map((rating) => (
                  <tr key={rating.id} className="hover:bg-foreground/[0.02] transition-colors">
                    <td className="text-foreground/50 px-5 py-3 font-mono text-xs whitespace-nowrap tabular-nums">
                      {formatDate(rating.created_at)}
                    </td>
                    <td className="px-5 py-3">
                      {rating.rating === 1 ? (
                        <span className="inline-flex items-center gap-1 rounded-full bg-green-500/10 px-2.5 py-0.5 font-mono text-[10px] font-semibold tracking-wider text-green-600 uppercase dark:text-green-400">
                          <ThumbsUp className="h-3 w-3" />
                          Like
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 rounded-full bg-red-500/10 px-2.5 py-0.5 font-mono text-[10px] font-semibold tracking-wider text-red-600 uppercase dark:text-red-400">
                          <ThumbsDown className="h-3 w-3" />
                          Dislike
                        </span>
                      )}
                    </td>
                    <td className="text-foreground/65 max-w-[180px] truncate px-5 py-3 text-xs">
                      {rating.comment || <span className="text-foreground/25">—</span>}
                    </td>
                    <td className="text-foreground/50 max-w-[260px] truncate px-5 py-3 text-xs">
                      {rating.message_content || "—"}
                    </td>
                    <td className="text-foreground/65 px-5 py-3 text-xs whitespace-nowrap">
                      {rating.user_name || rating.user_email || "—"}
                    </td>
                    <td className="px-5 py-3">
                      {rating.conversation_id && (
                        <Link
                          href={`/chat?id=${rating.conversation_id}`}
                          className="text-foreground/40 hover:text-foreground inline-flex items-center gap-1 font-mono text-[11px] tracking-wider uppercase transition-colors"
                        >
                          <ExternalLink className="h-3 w-3" />
                          View
                        </Link>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {totalPages > 1 && (
          <div className="border-foreground/10 flex items-center justify-between border-t px-5 py-3">
            <span className="text-foreground/40 font-mono text-[11px] tracking-wider uppercase">
              Page {page + 1} of {totalPages} · {ratings?.total.toLocaleString()} total
            </span>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page === 0}
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                className="rounded-full"
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= totalPages - 1}
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                className="rounded-full"
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

function StatTile({
  label,
  value,
  icon,
  accent,
}: {
  label: string;
  value: string | null;
  icon?: React.ReactNode;
  accent?: "green" | "red";
}) {
  return (
    <div className="border-foreground/10 bg-card rounded-2xl border p-5">
      <p className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">{label}</p>
      <div className="mt-3 flex items-baseline gap-2">
        {value === null ? (
          <div className="bg-foreground/[0.06] h-8 w-20 animate-pulse rounded-lg" />
        ) : (
          <>
            <span
              className={cn(
                "font-display text-3xl font-bold tracking-tight tabular-nums",
                accent === "green" && "text-green-600 dark:text-green-400",
                accent === "red" && "text-red-600 dark:text-red-400",
                !accent && "text-foreground",
              )}
            >
              {value}
            </span>
            {icon && (
              <span
                className={cn(
                  "mb-0.5",
                  accent === "green" && "text-green-500",
                  accent === "red" && "text-red-500",
                  !accent && "text-foreground/30",
                )}
              >
                {icon}
              </span>
            )}
          </>
        )}
      </div>
    </div>
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
      <p className="text-foreground/50 mb-2 font-mono text-[10px] tracking-wider uppercase">
        {label}
      </p>
      {payload.map((p) => (
        <div key={p.name} className="flex items-center gap-2">
          <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: p.color }} />
          <span className="text-foreground/65">{p.name}</span>
          <span className="text-foreground ml-3 font-semibold tabular-nums">{p.value}</span>
        </div>
      ))}
    </div>
  );
}
