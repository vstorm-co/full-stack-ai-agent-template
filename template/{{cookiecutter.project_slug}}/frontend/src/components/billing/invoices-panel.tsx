"use client";

import { format } from "date-fns";
import { Download, ExternalLink, FileText } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useInvoices } from "@/hooks";
import { formatCurrency } from "@/lib/utils";
import type { InvoiceStatus } from "@/types";

const statusVariant: Record<InvoiceStatus, "default" | "secondary" | "destructive" | "outline"> = {
  paid: "default",
  open: "secondary",
  draft: "outline",
  void: "outline",
  uncollectible: "destructive",
};

const statusLabel: Record<InvoiceStatus, string> = {
  paid: "Paid",
  open: "Open",
  draft: "Draft",
  void: "Void",
  uncollectible: "Uncollectible",
};


export function InvoicesPanel() {
  const { invoices, isLoading } = useInvoices();

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Invoices</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {Array.from({ length: 4 }, (_, i) => (
            <Skeleton key={i} className="h-14 w-full" />
          ))}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileText className="h-5 w-5" />
          Invoices
        </CardTitle>
        <CardDescription>Your billing history and downloadable invoices.</CardDescription>
      </CardHeader>
      <CardContent>
        {invoices.length === 0 ? (
          <p className="text-muted-foreground py-6 text-center text-sm">No invoices yet.</p>
        ) : (
          <div className="divide-y">
            {invoices.map((inv) => (
              <div key={inv.id} className="flex items-center justify-between gap-4 py-3 text-sm">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{inv.number ?? inv.id.slice(0, 8)}</span>
                    <Badge variant={statusVariant[inv.status]} className="text-[10px]">
                      {statusLabel[inv.status]}
                    </Badge>
                  </div>
                  <p className="text-muted-foreground text-xs">
                    {format(new Date(inv.period_start), "MMM d")}–
                    {format(new Date(inv.period_end), "MMM d, yyyy")}
                  </p>
                </div>
                <div className="shrink-0 text-right">
                  <p className="font-medium tabular-nums">
                    {formatCurrency(inv.amount_due, inv.currency)}
                  </p>
                  <div className="mt-1 flex items-center justify-end gap-1">
                    {inv.invoice_pdf && (
                      <Button variant="ghost" size="sm" className="h-6 gap-1 px-2 text-xs" asChild>
                        <a href={inv.invoice_pdf} target="_blank" rel="noopener noreferrer">
                          <Download className="h-3 w-3" />
                          PDF
                        </a>
                      </Button>
                    )}
                    {inv.hosted_invoice_url && (
                      <Button variant="ghost" size="sm" className="h-6 gap-1 px-2 text-xs" asChild>
                        <a href={inv.hosted_invoice_url} target="_blank" rel="noopener noreferrer">
                          <ExternalLink className="h-3 w-3" />
                          View
                        </a>
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
