"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  Cpu,
  Database,
  HardDrive,
  RefreshCw,
  Server,
  Wifi,
  Zap,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { LoadingState } from "@/components/states";
import { Button } from "@/components/ui";
import { apiClient } from "@/lib/api-client";
import { cn } from "@/lib/utils";

type ServiceStatus = "operational" | "degraded" | "outage" | "unknown";

interface ServiceHealth {
  key: string;
  name: string;
  description: string;
  icon: LucideIcon;
  status: ServiceStatus;
  uptime90d: number;
  latencyMs?: number;
  detail?: string;
}

interface BackendHealthResp {
  status?: string;
  database?: { status?: string; latency_ms?: number };
  redis?: { status?: string; latency_ms?: number };
  vector_store?: { status?: string; latency_ms?: number };
  stripe?: { status?: string };
  llm?: { status?: string; provider?: string };
  worker?: { status?: string };
}

const REFRESH_INTERVAL_MS = 30_000;

function statusFromString(s?: string): ServiceStatus {
  if (!s) return "unknown";
  const v = s.toLowerCase();
  if (["ok", "up", "operational", "ready", "healthy"].includes(v)) return "operational";
  if (["degraded", "slow"].includes(v)) return "degraded";
  if (["down", "outage", "fail", "failed", "error"].includes(v)) return "outage";
  return "unknown";
}

function buildServices(resp: BackendHealthResp | null): ServiceHealth[] {
  const overall = statusFromString(resp?.status);
  return [
    {
      key: "api",
      name: "API",
      description: "REST + WebSocket gateway",
      icon: Server,
      status: overall === "unknown" ? "operational" : overall,
      uptime90d: 99.94,
    },
    {
      key: "database",
      name: "Database",
      description: "PostgreSQL primary",
      icon: Database,
      status: statusFromString(resp?.database?.status),
      uptime90d: 99.97,
      latencyMs: resp?.database?.latency_ms,
    },
    {
      key: "redis",
      name: "Redis",
      description: "Cache & queue broker",
      icon: Zap,
      status: statusFromString(resp?.redis?.status),
      uptime90d: 99.96,
      latencyMs: resp?.redis?.latency_ms,
    },
    {
      key: "vector",
      name: "Vector store",
      description: "RAG embeddings backend",
      icon: HardDrive,
      status: statusFromString(resp?.vector_store?.status),
      uptime90d: 99.91,
      latencyMs: resp?.vector_store?.latency_ms,
    },
    {
      key: "llm",
      name: "LLM provider",
      description: resp?.llm?.provider ? `Provider: ${resp.llm.provider}` : "Default model API",
      icon: Cpu,
      status: statusFromString(resp?.llm?.status),
      uptime90d: 99.87,
    },
    {
      key: "stripe",
      name: "Stripe API",
      description: "Billing & payments",
      icon: Wifi,
      status: statusFromString(resp?.stripe?.status),
      uptime90d: 99.99,
    },
    {
      key: "worker",
      name: "Background worker",
      description: "Document ingestion + sync jobs",
      icon: Activity,
      status: statusFromString(resp?.worker?.status),
      uptime90d: 99.89,
    },
  ];
}

const STATUS_TONE: Record<ServiceStatus, string> = {
  operational: "border-brand/30 text-brand",
  degraded: "border-yellow-500/30 text-yellow-500",
  outage: "border-destructive/30 text-destructive",
  unknown: "border-foreground/15 text-foreground/55",
};

const STATUS_DOT: Record<ServiceStatus, string> = {
  operational: "bg-brand",
  degraded: "bg-yellow-500",
  outage: "bg-destructive",
  unknown: "bg-foreground/30",
};

const STATUS_LABEL: Record<ServiceStatus, string> = {
  operational: "Operational",
  degraded: "Degraded",
  outage: "Outage",
  unknown: "Unknown",
};

export default function SystemHealthPage() {
  const [resp, setResp] = useState<BackendHealthResp | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [auto, setAuto] = useState(true);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      // Try the detailed readiness endpoint first; fall back to /health.
      const ready = await apiClient.get<BackendHealthResp>("/health/ready").catch(() => null);
      const data = ready ?? (await apiClient.get<BackendHealthResp>("/health"));
      setResp(data);
      setLastChecked(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch health");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    if (!auto) return;
    const id = window.setInterval(load, REFRESH_INTERVAL_MS);
    return () => window.clearInterval(id);
  }, [auto]);

  const services = useMemo(() => buildServices(resp), [resp]);
  const overall: ServiceStatus = useMemo(() => {
    if (services.some((s) => s.status === "outage")) return "outage";
    if (services.some((s) => s.status === "degraded")) return "degraded";
    if (services.every((s) => s.status === "operational" || s.status === "unknown"))
      return "operational";
    return "unknown";
  }, [services]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="font-display text-foreground text-xl font-semibold tracking-tight">
            System health
          </h2>
          <p className="text-foreground/55 text-xs">
            Live readiness for each backing service. Auto-refreshes every 30s.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setAuto((a) => !a)}
            className={cn(
              "border-foreground/15 inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 font-mono text-[11px] tracking-wider uppercase transition-colors",
              auto
                ? "bg-foreground text-background border-foreground"
                : "text-foreground/65 hover:text-foreground hover:border-foreground/40",
            )}
          >
            <span
              aria-hidden
              className={cn(
                "h-1.5 w-1.5 rounded-full",
                auto ? "bg-brand animate-pulse" : "bg-foreground/40",
              )}
            />
            Auto-refresh {auto ? "on" : "off"}
          </button>
          <Button size="sm" variant="outline" onClick={load} className="rounded-full">
            <RefreshCw className={cn("mr-2 h-3.5 w-3.5", loading && "animate-spin")} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Overall banner */}
      <section
        className={cn(
          "border-foreground/10 bg-card relative overflow-hidden rounded-3xl border p-6 sm:p-8",
        )}
      >
        <div className="bg-brand/[0.06] pointer-events-none absolute -top-32 -right-32 h-72 w-72 rounded-full blur-[120px]" />
        <div className="relative flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <span
              className={cn(
                "flex h-12 w-12 items-center justify-center rounded-full",
                overall === "operational"
                  ? "bg-brand/15 text-foreground"
                  : overall === "outage"
                    ? "bg-destructive/15 text-destructive"
                    : "bg-yellow-500/15 text-yellow-500",
              )}
            >
              {overall === "outage" ? (
                <AlertCircle className="h-5 w-5" />
              ) : (
                <CheckCircle2 className="h-5 w-5" />
              )}
            </span>
            <div>
              <p className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">
                Overall
              </p>
              <p className="font-display text-foreground mt-0.5 text-2xl font-bold tracking-tight">
                {overall === "operational"
                  ? "All systems operational"
                  : overall === "outage"
                    ? "Active outage"
                    : overall === "degraded"
                      ? "Degraded performance"
                      : "Status unknown"}
              </p>
            </div>
          </div>
          {lastChecked && (
            <span className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">
              Checked {lastChecked.toLocaleTimeString()}
            </span>
          )}
        </div>
      </section>

      {/* Per-service grid */}
      {loading && !resp ? (
        <LoadingState variant="stats" rows={6} />
      ) : error ? (
        <div className="border-destructive/30 bg-destructive/[0.04] rounded-2xl border p-6 text-center">
          <AlertCircle className="text-destructive mx-auto h-6 w-6" />
          <p className="text-foreground mt-3 text-sm font-medium">Couldn&apos;t fetch health</p>
          <p className="text-foreground/65 mt-1 text-xs">{error}</p>
        </div>
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {services.map((s) => (
            <li
              key={s.key}
              className="border-foreground/10 bg-card flex flex-col gap-3 rounded-2xl border p-5"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-3">
                  <span className="bg-foreground/8 text-foreground inline-flex h-9 w-9 items-center justify-center rounded-full">
                    <s.icon className="h-4 w-4" />
                  </span>
                  <div>
                    <p className="text-foreground font-display text-sm font-semibold">{s.name}</p>
                    <p className="text-foreground/55 text-xs">{s.description}</p>
                  </div>
                </div>
                <span
                  className={cn(
                    "inline-flex shrink-0 items-center gap-1 rounded-full border px-2 py-0.5 font-mono text-[10px] font-semibold tracking-wider uppercase",
                    STATUS_TONE[s.status],
                  )}
                >
                  <span
                    aria-hidden
                    className={cn(
                      "h-1 w-1 rounded-full",
                      STATUS_DOT[s.status],
                      s.status === "operational" && "animate-pulse",
                    )}
                  />
                  {STATUS_LABEL[s.status]}
                </span>
              </div>
              <div className="border-foreground/8 text-foreground/55 mt-1 flex items-center justify-between gap-3 border-t pt-3 font-mono text-[10px] tracking-wider uppercase">
                <span>{s.uptime90d.toFixed(2)}% · 90d</span>
                {typeof s.latencyMs === "number" && <span>p50 {s.latencyMs}ms</span>}
              </div>
            </li>
          ))}
        </ul>
      )}

      <p className="text-foreground/45 inline-flex items-center gap-2 font-mono text-[11px] tracking-wider uppercase">
        Backend wishlist: <code className="font-mono">/health/ready</code> with per-service detail.
        90d uptime is currently illustrative.
      </p>
    </div>
  );
}
