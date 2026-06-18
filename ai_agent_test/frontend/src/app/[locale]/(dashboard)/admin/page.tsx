"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Activity,
  ArrowUpRight,
  CreditCard,
  MessageSquare,
  RefreshCw,
  Star,
  UserPlus,
  Users,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { LoadingState } from "@/components/states";
import { StatCard } from "@/components/dashboard/stat-card";
import { Button } from "@/components/ui";
import { apiClient } from "@/lib/api-client";
import { cn } from "@/lib/utils";

interface AdminStats {
  total_users?: number;
  active_users_24h?: number;
  total_conversations?: number;
  total_messages?: number;
  credits_charged_30d?: number;
  mrr_cents?: number;
}

interface RecentEvent {
  id: string;
  type: "user_signup" | "conversation_created" | "subscription_renewed" | "rating_low";
  title: string;
  description: string;
  timestamp: string;
}

const EVENT_ICON: Record<RecentEvent["type"], LucideIcon> = {
  user_signup: UserPlus,
  conversation_created: MessageSquare,
  subscription_renewed: CreditCard,
  rating_low: Star,
};

function formatRelative(iso: string): string {
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return "";
  const diff = Math.round((Date.now() - t) / 1000);
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export default function AdminOverviewPage() {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);
  const [events, setEvents] = useState<RecentEvent[] | null>(null);

  const loadStats = async () => {
    setStatsLoading(true);
    try {
      // Best-effort: call the backend admin stats endpoint if it exists.
      // Falls back to per-resource counts otherwise.
      const data = await apiClient.get<AdminStats>("/admin/stats").catch(() => null);
      if (data) {
        setStats(data);
      } else {
        const [usersResp, convsResp] = await Promise.allSettled([
          apiClient.get<{ total: number }>("/admin/users?limit=1"),
          apiClient.get<{ total: number }>("/admin/conversations?limit=1"),
        ]);
        setStats({
          total_users: usersResp.status === "fulfilled" ? usersResp.value.total : undefined,
          total_conversations: convsResp.status === "fulfilled" ? convsResp.value.total : undefined,
        });
      }
    } finally {
      setStatsLoading(false);
    }
  };

  const loadEvents = async () => {
    setEvents(null);
    try {
      // Backend wishlist: /admin/events. Fall back to recent conversations as
      // a stand-in so the surface isn't empty.
      const events = await apiClient
        .get<{ items: RecentEvent[] }>("/admin/events")
        .catch(() => null);
      if (events) {
        setEvents(events.items.slice(0, 8));
        return;
      }
      const convs = await apiClient
        .get<{
          items: Array<{ id: string; user_email?: string; title?: string; created_at: string }>;
        }>("/admin/conversations?limit=8")
        .catch(() => ({ items: [] }));
      setEvents(
        convs.items.map((c) => ({
          id: c.id,
          type: "conversation_created" as const,
          title: c.title || "New conversation",
          description: c.user_email ? `by ${c.user_email}` : "",
          timestamp: c.created_at,
        })),
      );
    } catch {
      setEvents([]);
    }
  };

  useEffect(() => {
    loadStats();
    loadEvents();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between gap-3">
        <div>
          <p className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">
            Overview
          </p>
          <h2 className="font-display text-foreground [&_em]:font-accent mt-1 text-xl font-semibold tracking-tight [&_em]:font-normal [&_em]:italic">
            The view from <em>above.</em>
          </h2>
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={() => {
            loadStats();
            loadEvents();
          }}
          className="rounded-full"
        >
          <RefreshCw className={cn("mr-2 h-3.5 w-3.5", statsLoading && "animate-spin")} />
          Refresh
        </Button>
      </div>

      {/* Stats strip */}
      {statsLoading ? (
        <LoadingState variant="stats" rows={4} />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            label="Total users"
            value={(stats?.total_users ?? 0).toLocaleString()}
            icon={Users}
          />
          <StatCard
            label="Active 24h"
            value={(stats?.active_users_24h ?? 0).toLocaleString()}
            icon={Activity}
            featured
          />
          <StatCard
            label="Conversations"
            value={(stats?.total_conversations ?? 0).toLocaleString()}
            icon={MessageSquare}
          />
          <StatCard
            label="MRR"
            value={
              typeof stats?.mrr_cents === "number"
                ? (stats.mrr_cents / 100).toLocaleString("en-US", {
                    style: "currency",
                    currency: "USD",
                    minimumFractionDigits: 0,
                  })
                : "—"
            }
            icon={CreditCard}
          />
        </div>
      )}

      {/* Quick actions */}
      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <QuickLink
          href="/admin/users"
          icon={Users}
          title="Manage users"
          description="Search, suspend, impersonate"
        />
        <QuickLink
          href="/admin/conversations"
          icon={MessageSquare}
          title="Browse chats"
          description="All conversations across users"
        />
        <QuickLink
          href="/admin/stripe-events"
          icon={CreditCard}
          title="Stripe events"
          description="Replay webhooks, debug billing"
        />
        <QuickLink
          href="/admin/system"
          icon={Activity}
          title="System health"
          description="Per-service status & uptime"
        />
        <QuickLink
          href="/admin/ratings"
          icon={Star}
          title="Response ratings"
          description="Quality signals from users"
        />
      </section>

      {/* Recent activity */}
      <section className="border-foreground/10 bg-card rounded-2xl border">
        <div className="border-foreground/10 flex items-center justify-between border-b px-6 py-5">
          <div>
            <h2 className="font-display text-foreground text-base font-semibold tracking-tight">
              Recent activity
            </h2>
            <p className="text-foreground/55 text-xs">
              Workspace-wide events. Backend wishlist:{" "}
              <code className="font-mono">/admin/events</code> for first-class feed.
            </p>
          </div>
        </div>
        {events === null ? (
          <div className="p-6">
            <LoadingState variant="skeleton-list" rows={5} />
          </div>
        ) : events.length === 0 ? (
          <div className="border-foreground/10 m-6 rounded-xl border-2 border-dashed p-10 text-center">
            <p className="text-foreground/65 text-sm">No recent events.</p>
          </div>
        ) : (
          <ul className="divide-foreground/10 divide-y">
            {events.map((e) => {
              const Icon = EVENT_ICON[e.type] ?? MessageSquare;
              return (
                <li key={e.id} className="flex items-center gap-3 px-6 py-4">
                  <span className="bg-foreground/8 text-foreground/80 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full">
                    <Icon className="h-4 w-4" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-foreground truncate text-sm font-medium">{e.title}</p>
                    <p className="text-foreground/55 truncate text-xs">
                      {e.description}
                      {e.description && " · "}
                      {formatRelative(e.timestamp)}
                    </p>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}

function QuickLink({
  href,
  icon: Icon,
  title,
  description,
}: {
  href: string;
  icon: LucideIcon;
  title: string;
  description: string;
}) {
  return (
    <Link
      href={href}
      className="lift border-foreground/10 hover:border-brand/40 bg-card group flex items-center gap-3 rounded-2xl border p-4 transition-all"
    >
      <span className="bg-brand/15 text-foreground group-hover:bg-brand group-hover:text-brand-foreground inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-xl transition-colors">
        <Icon className="h-4 w-4" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-foreground text-sm font-semibold">{title}</p>
        <p className="text-foreground/55 truncate text-xs">{description}</p>
      </div>
      <ArrowUpRight className="text-foreground/30 group-hover:text-foreground h-4 w-4 transition-all group-hover:rotate-45" />
    </Link>
  );
}
