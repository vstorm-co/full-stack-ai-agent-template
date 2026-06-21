"use client";

import { Download, FileText } from "lucide-react";

import { Badge, Button, DataTable, type Column } from "@/components/ui";
import { useInvoices } from "@/hooks";
import { cn, formatCurrency, formatDate } from "@/lib/utils";
import type { InvoiceRead } from "@/types";


const STATUS_TONES: Record<string, string> = {
  paid: "border-border text-foreground",
  open: "border-yellow-500/40 text-yellow-600 dark:text-yellow-500",
  draft: "border-border text-muted-foreground",
  void: "border-border text-muted-foreground",
  uncollectible: "border-destructive/40 text-destructive",
};

export default function InvoicesPage() {
  const { invoices, isLoading } = useInvoices();

  const columns: Column<InvoiceRead>[] = [
    {
      key: "date",
      header: "Date",
      cell: (inv) => (
        <div className="min-w-0">
          <p className="text-foreground font-medium">
            {inv.number ?? `Invoice ${inv.id.slice(0, 8)}`}
          </p>
          <p className="text-muted-foreground text-xs">
            {formatDate(inv.period_start)} — {formatDate(inv.period_end)}
          </p>
        </div>
      ),
    },
    {
      key: "amount",
      header: "Amount",
      align: "right",
      cell: (inv) => (
        <span className="font-mono tabular-nums">
          {formatCurrency(inv.amount_due, inv.currency, 2)}
        </span>
      ),
    },
    {
      key: "status",
      header: "Status",
      hideBelow: "sm",
      cell: (inv) => (
        <Badge
          variant="outline"
          className={cn(
            "font-mono text-[10px] uppercase",
            STATUS_TONES[inv.status] ?? "border-border text-muted-foreground",
          )}
        >
          {inv.status}
        </Badge>
      ),
    },
    {
      key: "download",
      header: "",
      align: "right",
      className: "w-16",
      cell: (inv) =>
        inv.invoice_pdf ? (
          <Button asChild variant="ghost" size="icon" className="shrink-0">
            <a
              href={inv.invoice_pdf}
              target="_blank"
              rel="noopener noreferrer"
              title="Download PDF"
              aria-label="Download invoice PDF"
            >
              <Download className="h-3.5 w-3.5" />
            </a>
          </Button>
        ) : (
          <span className="text-muted-foreground text-xs">—</span>
        ),
    },
  ];

  return (
    <div className="space-y-4">
      <DataTable
        columns={columns}
        rows={invoices}
        loading={isLoading}
        getRowKey={(inv) => inv.id}
        empty={
          <div className="flex flex-col items-center gap-2">
            <FileText className="text-muted-foreground h-7 w-7" />
            <p className="text-foreground text-sm">No invoices yet</p>
            <p className="text-muted-foreground text-xs">
              Invoices appear here after your first paid period.
            </p>
          </div>
        }
      />
    </div>
  );
}
