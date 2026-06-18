import type { ReactNode } from "react";

import { AdminNav } from "@/components/admin/admin-nav";
import { PageHero } from "@/components/dashboard/page-hero";

export default function AdminLayout({ children }: { children: ReactNode }) {
  return (
    <div className="mx-auto w-full max-w-7xl space-y-6 pb-10">
      <PageHero
        eyebrow="Admin · power-user tools"
        title={
          <>
            Operate the <em>workspace.</em>
          </>
        }
        description="Users, conversations, ratings, billing webhooks, system health — all in one place."
        actions={
          <span className="border-foreground/15 text-foreground/65 inline-flex items-center gap-2 rounded-full border px-3 py-1 font-mono text-[11px] tracking-wider uppercase">
            <span
              aria-hidden
              className="bg-brand h-1.5 w-1.5 animate-pulse rounded-full"
              style={{ boxShadow: "0 0 6px var(--color-brand)" }}
            />
            Admin role required
          </span>
        }
      />

      <div className="grid gap-6 lg:grid-cols-[200px_1fr] lg:gap-8">
        <aside className="lg:sticky lg:top-6 lg:self-start">
          <AdminNav />
        </aside>
        <div className="min-w-0">{children}</div>
      </div>
    </div>
  );
}
