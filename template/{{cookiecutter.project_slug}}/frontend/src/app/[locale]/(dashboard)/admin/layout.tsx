"use client";

import type { ReactNode } from "react";
import { Activity,{%- if cookiecutter.enable_billing %} CreditCard,{%- endif %} LayoutDashboard, MessageSquare, Star, Users } from "lucide-react";

import { ROUTES } from "@/lib/constants";
import { PageHeader } from "@/components/dashboard/page-header";
import { PageTabs, type PageTab } from "@/components/dashboard/page-tabs";

const ADMIN_TABS: PageTab[] = [
  { label: "Overview", href: ROUTES.ADMIN, icon: LayoutDashboard, exact: true },
  { label: "Users", href: ROUTES.ADMIN_USERS, icon: Users },
  { label: "Conversations", href: ROUTES.ADMIN_CONVERSATIONS, icon: MessageSquare },
  { label: "Ratings", href: ROUTES.ADMIN_RATINGS, icon: Star },
{%- if cookiecutter.enable_billing %}
  { label: "Stripe events", href: ROUTES.ADMIN_STRIPE_EVENTS, icon: CreditCard },
{%- endif %}
  { label: "System", href: ROUTES.ADMIN_SYSTEM, icon: Activity },
];

export default function AdminLayout({ children }: { children: ReactNode }) {
  return (
    <div className="space-y-6 pb-8">
      <PageHeader
        eyebrow="Admin"
        title="Workspace administration"
        description="Users, conversations, ratings, billing webhooks, and system health."
      />
      <PageTabs tabs={ADMIN_TABS} />
      <div className="min-w-0">{children}</div>
    </div>
  );
}
