"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowUpRight, Clock, Sparkles, XCircle } from "lucide-react";

import { apiClient } from "@/lib/api-client";
import { ROUTES } from "@/lib/constants";
import { cn } from "@/lib/utils";
import type { SubscriptionRead } from "@/types";

const TONE: Record<string, string> = {
  trialing: "bg-foreground/[0.04] text-foreground/80 border-foreground/15",
  active: "bg-muted text-foreground border-foreground/15",
  past_due: "bg-yellow-500/10 text-yellow-700 dark:text-yellow-300 border-yellow-500/30",
  canceled: "bg-destructive/10 text-destructive border-destructive/30",
  unpaid: "bg-destructive/10 text-destructive border-destructive/30",
  incomplete: "bg-foreground/[0.04] text-foreground/65 border-foreground/15",
  incomplete_expired: "bg-foreground/[0.04] text-foreground/55 border-foreground/15",
  paused: "bg-foreground/[0.04] text-foreground/65 border-foreground/15",
  free: "border-foreground/15 text-foreground/65",
};

function daysUntil(iso: string | null | undefined): number | null {
  if (!iso) return null;
  const target = new Date(iso).getTime();
  if (Number.isNaN(target)) return null;
  return Math.max(0, Math.ceil((target - Date.now()) / 86_400_000));
}

export function SubscriptionChip() {
  const [sub, setSub] = useState<SubscriptionRead | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    apiClient
      .get<SubscriptionRead | null>("/billing/me/subscription")
      .then((d) => {
        if (!cancelled) setSub(d);
      })
      .catch(() => {
        if (!cancelled) setSub(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return <span className="bg-foreground/8 inline-block h-5 w-24 animate-pulse rounded-full" />;
  }

  // No subscription = free tier
  if (!sub) {
    return (
      <Link
        href={ROUTES.PRICING}
        className={cn(
          "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 font-mono text-[11px] tracking-wider uppercase transition-colors",
          TONE.free,
          "hover:border-foreground/40 hover:text-foreground",
        )}
      >
        <Sparkles className="h-3 w-3" />
        Free · Upgrade
        <ArrowUpRight className="h-2.5 w-2.5" />
      </Link>
    );
  }

  const status = sub.status;
  const trialDays = daysUntil(sub.trial_end);
  const renewDays = daysUntil(sub.current_period_end);

  let label: string;
  let icon = <Clock className="h-3 w-3" />;

  if (status === "trialing" && trialDays !== null) {
    label = `Trial · ${trialDays}d left`;
  } else if (status === "active" && sub.cancel_at_period_end && renewDays !== null) {
    label = `Ends in ${renewDays}d`;
    icon = <XCircle className="h-3 w-3" />;
  } else if (status === "active" && renewDays !== null) {
    label = `Active · renews in ${renewDays}d`;
  } else if (status === "canceled") {
    label = renewDays !== null ? `Canceled · ${renewDays}d access` : "Canceled";
    icon = <XCircle className="h-3 w-3" />;
  } else if (status === "past_due") {
    label = "Past due — update payment";
  } else {
    label = status.replace(/_/g, " ");
  }

  return (
    <Link
      href={ROUTES.BILLING_SUBSCRIPTION}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 font-mono text-[11px] tracking-wider uppercase transition-colors hover:opacity-80",
        TONE[status] ?? TONE.free,
      )}
    >
      {icon}
      {label}
    </Link>
  );
}
