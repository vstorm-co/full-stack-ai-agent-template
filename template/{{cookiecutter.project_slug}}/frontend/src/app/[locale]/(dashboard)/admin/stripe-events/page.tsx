"use client";

import { useEffect, useMemo, useState } from "react";
import {
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Filter,
  RefreshCw,
  Search,
} from "lucide-react";
import { toast } from "sonner";

import {
  Button,
  DataTable,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Input,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  type Column,
} from "@/components/ui";
import { apiClient } from "@/lib/api-client";
import { cn, formatCurrency } from "@/lib/utils";

interface StripeEvent {
  id: string;
  type: string;
  status: "processed" | "failed" | "pending";
  livemode: boolean;
  customer_email?: string | null;
  amount_cents?: number | null;
  currency?: string | null;
  created_at: string;
  attempts: number;
  last_error?: string | null;
}

const PAGE_SIZE_OPTIONS = [25, 50, 100] as const;
type StatusFilter = "all" | "processed" | "failed" | "pending";

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

function formatAmount(
  cents: number | null | undefined,
  currency: string | null | undefined,
): string {
  if (typeof cents !== "number") return "—";
  return formatCurrency(cents, currency ?? "USD");
}

const STUB_EVENTS: StripeEvent[] = [
  {
    id: "evt_3PqWzL2eZvKYlo2C0K",
    type: "invoice.payment_succeeded",
    status: "processed",
    livemode: true,
    customer_email: "maya@lumenlabs.co",
    amount_cents: 2900,
    currency: "usd",
    created_at: new Date(Date.now() - 1000 * 60 * 18).toISOString(),
    attempts: 1,
  },
  {
    id: "evt_3PqWzM2eZvKYlo2DRT",
    type: "customer.subscription.updated",
    status: "processed",
    livemode: true,
    customer_email: "jonas@stash.ai",
    created_at: new Date(Date.now() - 1000 * 60 * 47).toISOString(),
    attempts: 1,
  },
  {
    id: "evt_3PqWzN2eZvKYlo2EX7",
    type: "invoice.payment_failed",
    status: "failed",
    livemode: true,
    customer_email: "ops@northwind.io",
    amount_cents: 9900,
    currency: "usd",
    created_at: new Date(Date.now() - 1000 * 60 * 90).toISOString(),
    attempts: 3,
    last_error: "Card declined: insufficient_funds",
  },
  {
    id: "evt_3PqWzO2eZvKYlo2F8M",
    type: "checkout.session.completed",
    status: "processed",
    livemode: true,
    customer_email: "priya@example.io",
    amount_cents: 2900,
    currency: "usd",
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 4).toISOString(),
    attempts: 1,
  },
  {
    id: "evt_3PqWzP2eZvKYlo2GZQ",
    type: "customer.subscription.deleted",
    status: "processed",
    livemode: false,
    customer_email: "test@example.com",
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 8).toISOString(),
    attempts: 1,
  },
  {
    id: "evt_3PqWzQ2eZvKYlo2HHb",
    type: "invoice.created",
    status: "pending",
    livemode: true,
    customer_email: "billing@megacorp.com",
    amount_cents: 49900,
    currency: "usd",
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 12).toISOString(),
    attempts: 0,
  },
];

export default function StripeEventsPage() {
  const [events, setEvents] = useState<StripeEvent[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [pageSize, setPageSize] = useState(50);
  const [page, setPage] = useState(0);
  const [selected, setSelected] = useState<StripeEvent | null>(null);
  const [usingStub, setUsingStub] = useState(false);
  const [replaying, setReplaying] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const data = await apiClient
        .get<{ items: StripeEvent[] }>("/admin/stripe-events?limit=500")
        .catch(() => null);
      if (data) {
        setEvents(data.items);
        setUsingStub(false);
      } else {
        setEvents(STUB_EVENTS);
        setUsingStub(true);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    setPage(0);
  }, [search, statusFilter, pageSize]);

  const filtered = useMemo(() => {
    if (!events) return [];
    const q = search.trim().toLowerCase();
    return events
      .filter((e) => {
        if (statusFilter !== "all" && e.status !== statusFilter) return false;
        if (q) {
          return (
            e.id.toLowerCase().includes(q) ||
            e.type.toLowerCase().includes(q) ||
            (e.customer_email ?? "").toLowerCase().includes(q)
          );
        }
        return true;
      })
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  }, [events, search, statusFilter]);

  const total = filtered.length;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const pageItems = useMemo(
    () => filtered.slice(page * pageSize, (page + 1) * pageSize),
    [filtered, page, pageSize],
  );

  const handleReplay = async (evt: StripeEvent) => {
    if (usingStub) {
      toast.info("Demo mode — backend wiring required (POST /admin/stripe-events/{id}/replay)");
      return;
    }
    setReplaying(evt.id);
    try {
      await apiClient.post(`/admin/stripe-events/${evt.id}/replay`);
      toast.success(`Replayed ${evt.type}`);
      await load();
    } catch {
      toast.error("Replay failed");
    } finally {
      setReplaying(null);
    }
  };

  const columns: Column<StripeEvent>[] = [
    {
      key: "type",
      header: "Event",
      cell: (e) => (
        <div className="min-w-0">
          <p className="text-foreground truncate font-medium">{e.type}</p>
          <p className="text-muted-foreground truncate font-mono text-xs">{e.id}</p>
        </div>
      ),
    },
    {
      key: "customer",
      header: "Customer",
      hideBelow: "md",
      cell: (e) => <span className="text-muted-foreground">{e.customer_email ?? "—"}</span>,
    },
    {
      key: "amount",
      header: "Amount",
      align: "right",
      hideBelow: "sm",
      className: "tabular-nums",
      cell: (e) => formatAmount(e.amount_cents, e.currency),
    },
    {
      key: "status",
      header: "Status",
      cell: (e) => <StatusBadge status={e.status} attempts={e.attempts} />,
    },
    {
      key: "created",
      header: "Time",
      hideBelow: "lg",
      cell: (e) => (
        <span className="text-muted-foreground text-xs whitespace-nowrap">
          {formatDateTime(e.created_at)}
        </span>
      ),
    },
    {
      key: "actions",
      header: "",
      align: "right",
      className: "w-px",
      cell: (e) => (
        <Button
          variant="ghost"
          size="sm"
          disabled={replaying === e.id}
          onClick={(ev) => {
            ev.stopPropagation();
            handleReplay(e);
          }}
          aria-label="Replay event"
        >
          <RefreshCw className={cn("h-3.5 w-3.5", replaying === e.id && "animate-spin")} />
        </Button>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      {usingStub && (
        <div className="border-border bg-muted flex items-start gap-3 rounded-xl border p-3">
          <Filter className="text-muted-foreground mt-0.5 h-4 w-4 shrink-0" />
          <div className="min-w-0 flex-1 text-xs">
            <p className="text-foreground font-medium">Demo data</p>
            <p className="text-muted-foreground mt-0.5">
              Backend wiring required. Expected: <code className="font-mono">GET /admin/stripe-events</code>,{" "}
              <code className="font-mono">POST /admin/stripe-events/&#123;id&#125;/replay</code>.
            </p>
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <div className="relative min-w-[240px] flex-1">
          <Search className="text-muted-foreground absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
          <Input
            placeholder="Search id, type, customer…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10"
          />
        </div>

        <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v as StatusFilter)}>
          <SelectTrigger className="w-[140px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="processed">Processed</SelectItem>
            <SelectItem value="failed">Failed</SelectItem>
            <SelectItem value="pending">Pending</SelectItem>
          </SelectContent>
        </Select>

        <Select value={String(pageSize)} onValueChange={(v) => setPageSize(Number(v))}>
          <SelectTrigger className="w-[110px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {PAGE_SIZE_OPTIONS.map((n) => (
              <SelectItem key={n} value={String(n)}>
                {n} / page
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Button size="sm" variant="outline" onClick={load} disabled={loading}>
          <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
          Refresh
        </Button>
      </div>

      <div className="text-muted-foreground text-xs">{total} total</div>

      <DataTable
        columns={columns}
        rows={pageItems}
        getRowKey={(e) => e.id}
        loading={loading && events === null}
        onRowClick={(e) => setSelected(e)}
        empty="No events match."
      />

      {total > 0 && (
        <div className="border-border bg-card flex items-center justify-between rounded-xl border px-4 py-3">
          <span className="text-muted-foreground text-sm">
            {page * pageSize + 1}–{Math.min(total, (page + 1) * pageSize)} of {total}
          </span>
          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0 || loading}
              aria-label="Previous page"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="text-muted-foreground px-2 text-sm tabular-nums">
              {page + 1} / {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1 || loading}
              aria-label="Next page"
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      <EventDetailDialog
        event={selected}
        replaying={selected ? replaying === selected.id : false}
        onReplay={handleReplay}
        onClose={() => setSelected(null)}
      />
    </div>
  );
}

function StatusBadge({ status, attempts }: { status: StripeEvent["status"]; attempts: number }) {
  const suffix = attempts > 1 ? ` · ${attempts}×` : "";
  const styles: Record<StripeEvent["status"], string> = {
    processed: "border-border bg-muted text-foreground",
    failed: "border-destructive/30 bg-destructive/10 text-destructive",
    pending: "border-border bg-muted text-muted-foreground",
  };
  const label = { processed: "Processed", failed: "Failed", pending: "Pending" }[status];
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium whitespace-nowrap",
        styles[status],
      )}
    >
      {label}
      {status !== "pending" ? suffix : ""}
    </span>
  );
}

function EventDetailDialog({
  event,
  replaying,
  onReplay,
  onClose,
}: {
  event: StripeEvent | null;
  replaying: boolean;
  onReplay: (e: StripeEvent) => void;
  onClose: () => void;
}) {
  return (
    <Dialog open={event !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="bg-card border-border max-w-2xl rounded-xl">
        {event && (
          <>
            <DialogHeader>
              <DialogTitle className="font-mono text-sm break-all">{event.type}</DialogTitle>
              <DialogDescription className="font-mono text-xs break-all">
                {event.id}
              </DialogDescription>
            </DialogHeader>

            <dl className="grid gap-3 text-xs sm:grid-cols-2">
              <KV label="Mode" value={event.livemode ? "live" : "test"} />
              <KV label="Status" value={event.status} />
              <KV label="Attempts" value={String(event.attempts)} />
              <KV label="Created" value={formatDateTime(event.created_at)} />
              {event.customer_email && <KV label="Customer" value={event.customer_email} />}
              {typeof event.amount_cents === "number" && (
                <KV label="Amount" value={formatAmount(event.amount_cents, event.currency)} />
              )}
              {event.last_error && (
                <KV label="Last error" value={event.last_error} accent="danger" />
              )}
            </dl>

            <div className="space-y-1.5">
              <p className="text-muted-foreground font-mono text-[10px] tracking-wider uppercase">
                Payload
              </p>
              <pre className="bg-muted border-border text-foreground max-h-64 overflow-auto rounded-xl border p-3 font-mono text-xs leading-relaxed">
                {JSON.stringify(event, null, 2)}
              </pre>
            </div>

            <DialogFooter className="gap-2 sm:justify-between">
              <a
                href={`https://dashboard.stripe.com/${event.livemode ? "" : "test/"}events/${event.id}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-muted-foreground hover:text-foreground inline-flex items-center gap-1.5 text-xs"
              >
                Open in Stripe
                <ExternalLink className="h-3 w-3" />
              </a>
              <Button size="sm" variant="outline" disabled={replaying} onClick={() => onReplay(event)}>
                <RefreshCw className={cn("h-3.5 w-3.5", replaying && "animate-spin")} />
                Replay
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}

function KV({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: "danger";
}) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-muted-foreground font-mono text-[10px] tracking-wider uppercase">
        {label}
      </dt>
      <dd className={cn("break-all", accent === "danger" ? "text-destructive" : "text-foreground")}>
        {value}
      </dd>
    </div>
  );
}
