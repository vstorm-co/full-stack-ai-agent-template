"use client";

import type { ReactNode } from "react";
import { BarChart3, CreditCard, FileText, LayoutDashboard, Sparkles, Wallet } from "lucide-react";

import { ROUTES } from "@/lib/constants";
import { PageHeader } from "@/components/dashboard/page-header";
import { PageTabs, type PageTab } from "@/components/dashboard/page-tabs";

const BILLING_TABS: PageTab[] = [
  { label: "Overview", href: ROUTES.BILLING, icon: LayoutDashboard, exact: true },
  { label: "Usage", href: ROUTES.BILLING_USAGE, icon: BarChart3 },
  { label: "Credits", href: ROUTES.BILLING_CREDITS, icon: Sparkles },
  { label: "Invoices", href: ROUTES.BILLING_INVOICES, icon: FileText },
  { label: "Payment methods", href: ROUTES.BILLING_PAYMENT_METHODS, icon: Wallet },
  { label: "Subscription", href: ROUTES.BILLING_SUBSCRIPTION, icon: CreditCard },
];

export default function BillingLayout({ children }: { children: ReactNode }) {
  return (
    <div className="space-y-6 pb-8">
      <PageHeader
        eyebrow="Billing"
        title="Billing & usage"
        description="Plan, credits, invoices, payment methods, and usage."
      />
      <PageTabs tabs={BILLING_TABS} />
      <div className="min-w-0">{children}</div>
    </div>
  );
}
