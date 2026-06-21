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
import { cn, getErrorMessage } from "@/lib/utils";

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

const STATUS_DOT: Record<ServiceStatus, string> = {
  operational: "bg-chart",
  degraded: "bg-muted-foreground",
  outage: "bg-destructive",
  unknown: "bg-muted-foreground",
};

const STATUS_LABEL: Record<ServiceStatus, string> = {
  operational: "Operational",
  degraded: "Degraded",
  outage: "Outage",
  unknown: "Unknown",
};

const STATUS_TEXT: Record<ServiceStatus, string> = {
  operational: "text-foreground",
  degraded: "text-foreground",
  outage: "text-destructive",
  unknown: "text-muted-foreground",
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
      setError(getErrorMessage(err, "Failed to fetch health"));
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

  const overallLabel =
    overall === "operational"
      ? "All systems operational"
      : overall === "outage"
        ? "Active outage"
        : overall === "degraded"
          ? "Degraded performance"
          : "Status unknown";

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-end gap-2">
        <Button
          size="sm"
          variant="outline"
          onClick={() => setAuto((a) => !a)}
          className={cn(auto && "bg-muted")}
        >
          <span
            aria-hidden
            className={cn(
              "h-1.5 w-1.5 rounded-full",
              auto ? "bg-chart" : "bg-muted-foreground",
            )}
          />
          Auto-refresh {auto ? "on" : "off"}
        </Button>
        <Button size="sm" variant="outline" onClick={load}>
          <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
          Refresh
        </Button>
      </div>

      <section className="border-border bg-card rounded-xl border p-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="bg-muted text-foreground inline-flex h-10 w-10 items-center justify-center rounded-lg">
              {overall === "outage" ? (
                <AlertCircle className="h-5 w-5" />
              ) : (
                <CheckCircle2 className="h-5 w-5" />
              )}
            </span>
            <div>
              <p className="text-muted-foreground text-xs">Overall status</p>
              <div className="mt-1 flex items-center gap-2">
                <span
                  aria-hidden
                  className={cn("h-2 w-2 rounded-full", STATUS_DOT[overall])}
                />
                <p className="text-foreground text-base font-semibold">{overallLabel}</p>
              </div>
            </div>
          </div>
          {lastChecked && (
            <span className="text-muted-foreground text-xs">
              Checked {lastChecked.toLocaleTimeString()}
            </span>
          )}
        </div>
      </section>

      {loading && !resp ? (
        <LoadingState variant="stats" rows={6} />
      ) : error ? (
        <div className="border-border bg-card rounded-xl border p-8 text-center">
          <AlertCircle className="text-destructive mx-auto h-6 w-6" />
          <p className="text-foreground mt-3 text-sm font-medium">Couldn&apos;t fetch health</p>
          <p className="text-muted-foreground mt-1 text-xs">{error}</p>
        </div>
      ) : (
        <section className="border-border bg-card rounded-xl border">
          <div className="border-border border-b px-5 py-4">
            <h2 className="text-foreground text-sm font-semibold">Services</h2>
            <p className="text-muted-foreground text-xs">
              Live readiness for each backing service. Auto-refreshes every 30s.
            </p>
          </div>
          <ul className="divide-border divide-y">
            {services.map((s) => (
              <li key={s.key} className="flex items-center gap-3 px-5 py-4">
                <span className="bg-muted text-muted-foreground inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg">
                  <s.icon className="h-4 w-4" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-foreground truncate text-sm font-medium">{s.name}</p>
                  <p className="text-muted-foreground truncate text-xs">{s.description}</p>
                </div>
                <div className="hidden text-right sm:block">
                  <p className="text-foreground text-xs tabular-nums">
                    {s.uptime90d.toFixed(2)}%
                  </p>
                  <p className="text-muted-foreground text-[11px]">
                    90d{typeof s.latencyMs === "number" ? ` · p50 ${s.latencyMs}ms` : ""}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-2 pl-1">
                  <span
                    aria-hidden
                    className={cn("h-2 w-2 rounded-full", STATUS_DOT[s.status])}
                  />
                  <span
                    className={cn(
                      "text-xs font-medium whitespace-nowrap",
                      STATUS_TEXT[s.status],
                    )}
                  >
                    {STATUS_LABEL[s.status]}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      <p className="text-muted-foreground text-xs">
        Backend wishlist: <code className="font-mono">/health/ready</code> with per-service detail.
        90d uptime is currently illustrative.
      </p>
    </div>
  );
}
