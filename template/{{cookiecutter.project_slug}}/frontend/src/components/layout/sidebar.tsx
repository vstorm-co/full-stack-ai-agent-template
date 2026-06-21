"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { cn, isAppAdmin } from "@/lib/utils";
import { APP_NAME, ROUTES } from "@/lib/constants";
import {
  LayoutDashboard,
  MessageSquare,
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
  Database,
{%- endif %}
  UserCircle,
  ShieldAlert,
{%- if cookiecutter.enable_teams %}
  Building2,
{%- endif %}
{%- if cookiecutter.enable_billing %}
  CreditCard,
{%- endif %}
} from "lucide-react";
import { useSidebarStore, useAuthStore } from "@/stores";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetClose } from "@/components/ui";

const navigation = [
  { nameKey: "dashboard", href: ROUTES.DASHBOARD, icon: LayoutDashboard },
  { nameKey: "chat", href: ROUTES.CHAT, icon: MessageSquare },
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
  { nameKey: "rag", href: ROUTES.KB, icon: Database },
{%- endif %}
{%- if cookiecutter.enable_teams %}
  { nameKey: "organizations", href: ROUTES.ORGS, icon: Building2 },
{%- endif %}
{%- if cookiecutter.enable_billing %}
  { nameKey: "billing", href: ROUTES.BILLING, icon: CreditCard },
{%- endif %}
  { nameKey: "profile", href: ROUTES.PROFILE, icon: UserCircle },
];

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const { user } = useAuthStore();
  const t = useTranslations("nav");

  return (
    <nav className="flex-1 space-y-1 p-4">
      {navigation.map((item) => {
        const isActive = pathname === item.href;
        return (
          <Link
            key={item.nameKey}
            href={item.href}
            onClick={onNavigate}
            className={cn(
              "flex items-center gap-3 rounded-lg px-3 py-3 text-sm font-medium transition-colors",
              "min-h-[44px]",
              isActive
                ? "bg-secondary text-secondary-foreground"
                : "text-muted-foreground hover:bg-secondary/50 hover:text-secondary-foreground",
            )}
          >
            <item.icon className="h-5 w-5" />
            {t(item.nameKey)}
          </Link>
        );
      })}
      {isAppAdmin(user) && (
        <Link
          href={ROUTES.ADMIN}
          onClick={onNavigate}
          className={cn(
            "flex items-center gap-3 rounded-lg px-3 py-3 text-sm font-medium transition-colors",
            "min-h-[44px]",
            pathname.startsWith("/admin")
              ? "bg-secondary text-secondary-foreground"
              : "text-muted-foreground hover:bg-secondary/50 hover:text-secondary-foreground",
          )}
        >
          <ShieldAlert className="h-5 w-5" />
          Admin
        </Link>
      )}
    </nav>
  );
}

export function Sidebar() {
  const { isOpen, close } = useSidebarStore();

  return (
    <Sheet open={isOpen} onOpenChange={close}>
      <SheetContent side="left" className="w-72 p-0">
        <SheetHeader className="h-14 px-4">
          <SheetTitle>{APP_NAME}</SheetTitle>
          <SheetClose onClick={close} />
        </SheetHeader>
        <NavLinks onNavigate={close} />
      </SheetContent>
    </Sheet>
  );
}
