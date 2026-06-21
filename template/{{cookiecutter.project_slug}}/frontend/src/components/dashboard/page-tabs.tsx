"use client";

import Link from "next/link";
import type { LucideIcon } from "lucide-react";

import { useActiveRoute } from "@/lib/active-route";
import { cn } from "@/lib/utils";

export interface PageTab {
  label: string;
  href: string;
  icon?: LucideIcon;
  /** Match only the exact path (use for index/overview tabs). */
  exact?: boolean;
}

/**
 * Flat, underline-style horizontal tabs that sit under a PageHeader and replace
 * nested left sidebars. The active state is a bottom border on the tab itself
 * (not an absolutely-positioned bar) so the horizontal scroll container never
 * produces a stray vertical scrollbar. The scrollbar is hidden; tabs scroll
 * horizontally only when they overflow (mobile).
 */
export function PageTabs({ tabs, className }: { tabs: PageTab[]; className?: string }) {
  const isActive = useActiveRoute();
  return (
    <div className={cn("border-border border-b", className)}>
      <nav className="-mb-px flex gap-0.5 overflow-x-auto [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        {tabs.map((tab) => {
          const active = isActive(tab.href, tab.exact);
          return (
            <Link
              key={tab.href}
              href={tab.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "inline-flex shrink-0 items-center gap-1.5 border-b-2 px-3.5 py-2.5 text-sm font-medium whitespace-nowrap transition-colors",
                active
                  ? "border-foreground text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground",
              )}
            >
              {tab.icon && <tab.icon className="h-4 w-4" />}
              {tab.label}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
