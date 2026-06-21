"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  CreditCard,
  Database,
  List,
  MessageSquare,
  Plus,
  Sparkles,
  Star,
} from "lucide-react";
import { ActiveSessions } from "@/components/dashboard/active-sessions";
import { OnboardingBanner } from "@/components/dashboard/onboarding-banner";
import { PageHeader } from "@/components/dashboard/page-header";
import { QuickActions } from "@/components/dashboard/quick-actions";
import { RecentActivity } from "@/components/dashboard/recent-activity";
import { SegmentedControl } from "@/components/dashboard/segmented-control";
import { StatCard } from "@/components/dashboard/stat-card";
import { SubscriptionChip } from "@/components/dashboard/subscription-chip";
import { TeamSummary } from "@/components/dashboard/team-summary";
import { ToolUsage } from "@/components/dashboard/tool-usage";
import { TopModels } from "@/components/dashboard/top-models";
import { UsageTimeline } from "@/components/dashboard/usage-timeline";
import { Button } from "@/components/ui";
import { useAuth } from "@/hooks";
import { apiClient } from "@/lib/api-client";
import { ROUTES } from "@/lib/constants";
import { getCollectionInfo, listCollections } from "@/lib/rag-api";
import { cn, isAppAdmin } from "@/lib/utils";
import type { HealthResponse } from "@/types";
interface CreditBalance {
  balance: number;
  low_threshold: number;
}
interface UsageBucket {
  day: string;
  credits_charged: number;
  total_calls: number;
}
interface UsageTimelineRead {
  buckets: UsageBucket[];
  days: number;
}
interface ConversationsResponse {
  total?: number;
  items: Array<{ id: string }>;
}

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}
function pctDelta(current: number[], prior: number[]): number | undefined {
  const cur = current.reduce((a, b) => a + b, 0);
  const prev = prior.reduce((a, b) => a + b, 0);
  if (prev === 0) return cur > 0 ? 100 : 0;
  return ((cur - prev) / prev) * 100;
}

export default function DashboardPage() {
  const { user } = useAuth();
  const [period, setPeriod] = useState<7 | 30 | 90>(7);

  // All independent → run in parallel, cached by React Query.
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => apiClient.get<HealthResponse>("/health"),
    staleTime: 60_000,
  });
  const credits = useQuery({
    queryKey: ["billing", "credits"],
    queryFn: () => apiClient.get<CreditBalance>("/billing/me/credits"),
  });
  const conversations = useQuery({
    queryKey: ["conversations", "count"],
    queryFn: async () => {
      const d = await apiClient.get<ConversationsResponse>("/conversations?limit=1");
      return d.total ?? d.items?.length ?? 0;
    },
  });
  const rag = useQuery({
    queryKey: ["rag", "stats"],
    queryFn: async () => {
      const list = await listCollections();
      const infos = await Promise.all(
        list.items.map((name) => getCollectionInfo(name).catch(() => null)),
      );
      return {
        collections: list.items.length,
        vectors: infos.reduce((s, i) => s + (i?.total_vectors ?? 0), 0),
      };
    },
  });
  const timelineQuery = useQuery({
    queryKey: ["billing", "timeline", period],
    queryFn: () =>
      apiClient
        .get<UsageTimelineRead>(`/billing/me/credits/usage/timeline?days=${period * 2}`)
        .then((d) => d.buckets),
  });
  const timeline = timelineQuery.data ?? null;

  const creditsSpark = (timeline ?? []).slice(-period).map((b) => b.credits_charged);
  const callsSpark = (timeline ?? []).slice(-period).map((b) => b.total_calls);
  const creditsDelta = timeline
    ? pctDelta(
        timeline.slice(-period).map((b) => b.credits_charged),
        timeline.slice(-period * 2, -period).map((b) => b.credits_charged),
      )
    : undefined;
  const callsDelta = timeline
    ? pctDelta(
        timeline.slice(-period).map((b) => b.total_calls),
        timeline.slice(-period * 2, -period).map((b) => b.total_calls),
      )
    : undefined;
  const deltaLabel = `vs prior ${period}d`;

  const firstName = user?.full_name?.split(" ")[0] || user?.email?.split("@")[0];
  const healthy = !health.isError;

  return (
    <div className="space-y-6 pb-8">
      <OnboardingBanner />

      <PageHeader
        eyebrow="Dashboard"
        title={firstName ? `${getGreeting()}, ${firstName}` : getGreeting()}
        description="Here's what's happening with your workspace today."
        actions={
          <Button asChild>
            <Link href={ROUTES.CHAT}>
              <Plus className="h-4 w-4" />
              New chat
            </Link>
          </Button>
        }
      />

      <div className="border-border bg-card flex flex-wrap items-center gap-x-6 gap-y-2 rounded-xl border px-4 py-3 text-sm">
        <span className="inline-flex items-center gap-2">
          <span
            aria-hidden
            className={cn(
              "inline-block h-2 w-2 rounded-full",
              healthy ? "bg-emerald-500" : "bg-destructive",
            )}
          />
          <span className="text-foreground font-medium">
            {healthy ? health.data?.status || "Operational" : "API offline"}
          </span>
        </span>
        {health.data?.version && (
          <span className="text-muted-foreground font-mono text-xs">v{health.data.version}</span>
        )}
        <span className="text-muted-foreground inline-flex items-center gap-1.5 text-xs">
          <Database className="h-3.5 w-3.5" />
          {rag.data ? `${rag.data.collections} collections` : "—"}
        </span>
        <span className="ml-auto inline-flex items-center gap-2">
          <span className="text-muted-foreground text-xs">Plan</span>
          <SubscriptionChip />
        </span>
      </div>

      <div className="flex items-center justify-between">
        <h2 className="text-muted-foreground font-mono text-xs tracking-wider uppercase">
          Workspace metrics
        </h2>
        <SegmentedControl
          value={String(period)}
          onChange={(v) => setPeriod(Number(v) as 7 | 30 | 90)}
          options={[
            { label: "7d", value: "7" },
            { label: "30d", value: "30" },
            { label: "90d", value: "90" },
          ]}
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Credits balance"
          value={credits.isLoading ? "—" : (credits.data?.balance ?? 0).toLocaleString()}
          icon={Sparkles}
          delta={creditsDelta}
          deltaLabel={deltaLabel}
          footer={
            credits.data
              ? `${credits.data.low_threshold.toLocaleString()} low threshold`
              : undefined
          }
          spark={creditsSpark.length >= 2 ? creditsSpark : undefined}
          loading={credits.isLoading}
        />
        <StatCard
          label="Conversations"
          value={conversations.isLoading ? "—" : (conversations.data ?? 0).toLocaleString()}
          icon={MessageSquare}
          footer="across all chats"
          loading={conversations.isLoading}
        />
        <StatCard
          label={`API calls (${period}d)`}
          value={timeline ? callsSpark.reduce((a, b) => a + b, 0).toLocaleString() : "—"}
          icon={Activity}
          delta={callsDelta}
          deltaLabel={deltaLabel}
          spark={callsSpark.length >= 2 ? callsSpark : undefined}
          loading={!timeline}
        />
        <StatCard
          label="Knowledge base"
          value={rag.data ? rag.data.vectors.toLocaleString() : "—"}
          unit={rag.data ? `vector${rag.data.vectors === 1 ? "" : "s"}` : undefined}
          icon={Database}
          footer={
            rag.data
              ? `${rag.data.collections} collection${rag.data.collections === 1 ? "" : "s"} indexed`
              : "indexed vectors"
          }
          loading={rag.isLoading}
        />
      </div>
      <div className="flex justify-end">
        <Link
          href={ROUTES.BILLING}
          className="text-muted-foreground hover:text-foreground inline-flex items-center gap-1.5 text-xs transition-colors"
        >
          <CreditCard className="h-3.5 w-3.5" />
          Manage billing →
        </Link>
      </div>
      <UsageTimeline />

      <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <RecentActivity />
        <TopModels />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <ToolUsage />
        <TeamSummary />
      </div>
      <ActiveSessions />

      <QuickActions />

      {isAppAdmin(user) && (
        <div>
          <h2 className="font-display text-foreground mb-3 text-base font-semibold">
            Admin actions
          </h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <AdminTile
              icon={Star}
              label="Response ratings"
              description="View and manage ratings"
              href={ROUTES.ADMIN_RATINGS}
            />
            <AdminTile
              icon={List}
              label="All conversations"
              description="Inspect any user's chats"
              href={ROUTES.ADMIN_CONVERSATIONS}
            />
          </div>
        </div>
      )}
    </div>
  );
}

function AdminTile({
  icon: Icon,
  label,
  description,
  href,
}: {
  icon: typeof Star;
  label: string;
  description: string;
  href: string;
}) {
  return (
    <Link
      href={href}
      className="border-border hover:border-foreground/30 bg-card hover:bg-accent flex items-center gap-3 rounded-xl border p-4 transition-colors"
    >
      <span className="bg-foreground/8 text-foreground flex h-9 w-9 items-center justify-center rounded-full">
        <Icon className="h-4 w-4" />
      </span>
      <div className="flex-1">
        <p className="text-foreground text-sm font-semibold">{label}</p>
        <p className="text-muted-foreground text-xs">{description}</p>
      </div>
    </Link>
  );
}
