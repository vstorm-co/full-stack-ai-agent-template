"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Coins, MessageSquare, Receipt, Sparkles } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { EmptyState, ErrorState, LoadingState } from "@/components/states";
import { apiClient } from "@/lib/api-client";
import { ROUTES } from "@/lib/constants";
import { cn } from "@/lib/utils";

interface ActivityItem {
  id: string;
  icon: LucideIcon;
  title: string;
  description?: string;
  timestamp: string;
  href?: string;
  accent?: "default" | "brand" | "danger";
}

interface ConversationItem {
  id: string;
  title?: string | null;
  created_at: string;
  updated_at?: string | null;
}

interface CreditTx {
  id: string;
  delta: number;
  type: string;
  description?: string | null;
  created_at: string;
}

export function RecentActivity({ limit = 6 }: { limit?: number }) {
  const [items, setItems] = useState<ActivityItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setError(null);
    setItems(null);
    try {
      const [convResp, txResp] = await Promise.allSettled([
        apiClient.get<{ items: ConversationItem[] }>("/conversations?limit=5"),
        apiClient.get<{ items: CreditTx[] }>("/billing/me/credits/transactions?limit=5"),
      ]);

      const events: ActivityItem[] = [];

      if (convResp.status === "fulfilled") {
        for (const c of convResp.value.items.slice(0, 4)) {
          events.push({
            id: `conv-${c.id}`,
            icon: MessageSquare,
            title: c.title?.trim() || "New conversation",
            description: "Conversation",
            timestamp: c.updated_at || c.created_at,
            href: `${ROUTES.CHAT}?id=${c.id}`,
          });
        }
      }

      if (txResp.status === "fulfilled") {
        for (const tx of txResp.value.items.slice(0, 4)) {
          const isPositive = tx.delta > 0;
          events.push({
            id: `tx-${tx.id}`,
            icon: isPositive ? Sparkles : tx.type === "subscription_renewal" ? Receipt : Coins,
            title:
              tx.description ||
              (isPositive
                ? `+${tx.delta.toLocaleString()} credits`
                : `${tx.delta.toLocaleString()} credits`),
            description: humanizeTxType(tx.type),
            timestamp: tx.created_at,
            accent: isPositive ? "brand" : tx.delta < 0 ? "default" : "default",
          });
        }
      }

      events.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
      setItems(events.slice(0, limit));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load activity");
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [limit]);

  return (
    <div className="border-border bg-card flex h-full flex-col rounded-2xl border p-5 lg:p-6">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="font-display text-foreground text-base font-semibold">Recent activity</h2>
        <Link
          href={ROUTES.CHAT}
          className="text-foreground/55 hover:text-foreground font-mono text-[11px] tracking-wider uppercase"
        >
          View all →
        </Link>
      </div>

      {items === null && !error && <LoadingState variant="skeleton-list" rows={4} />}
      {error && (
        <ErrorState
          title="Couldn't load activity"
          description={error}
          cta={{ label: "Retry", onClick: load }}
        />
      )}
      {items && items.length === 0 && !error && (
        <EmptyState
          icon={MessageSquare}
          title="Nothing yet"
          description="Start a chat or upload a document — recent events will appear here."
          cta={{ label: "Start a chat", href: ROUTES.CHAT }}
          fill
        />
      )}
      {items && items.length > 0 && (
        <ul className="-mx-2 flex-1 space-y-0.5">
          {items.map((item) => (
            <li key={item.id}>
              <ActivityRow item={item} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ActivityRow({ item }: { item: ActivityItem }) {
  const content = (
    <div
      className={cn(
        "hover:bg-foreground/[0.04] flex items-start gap-3 rounded-xl px-2 py-2.5 transition-colors",
      )}
    >
      <div
        className={cn(
          "flex h-9 w-9 shrink-0 items-center justify-center rounded-full",
          item.accent === "brand"
            ? "bg-brand/15 text-foreground"
            : item.accent === "danger"
              ? "bg-destructive/10 text-destructive"
              : "bg-foreground/8 text-foreground/80",
        )}
      >
        <item.icon className="h-4 w-4" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-foreground truncate text-sm font-medium">{item.title}</p>
        <p className="text-foreground/55 truncate text-xs">
          {item.description}
          {item.description && " · "}
          {formatRelative(item.timestamp)}
        </p>
      </div>
    </div>
  );

  if (item.href) {
    return <Link href={item.href}>{content}</Link>;
  }
  return content;
}

function formatRelative(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const diffSec = Math.round((Date.now() - then) / 1000);
  if (diffSec < 60) return "just now";
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
  if (diffSec < 86400 * 7) return `${Math.floor(diffSec / 86400)}d ago`;
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function humanizeTxType(t: string): string {
  return t.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());
}
