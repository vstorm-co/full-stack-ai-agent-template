"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Bell,
  Palette,
  Shield,
{%- if cookiecutter.use_auth and cookiecutter.use_ai %}
  Slash,
{%- endif %}
  UserCircle,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";
import { ROUTES } from "@/lib/constants";

interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  description: string;
}

const ITEMS: NavItem[] = [
  {
    label: "Profile",
    href: ROUTES.SETTINGS_PROFILE,
    icon: UserCircle,
    description: "Avatar, name, email, sessions",
  },
  {
    label: "Account",
    href: ROUTES.SETTINGS_ACCOUNT,
    icon: Shield,
    description: "Password, two-factor, danger zone",
  },
{%- if cookiecutter.use_auth and cookiecutter.use_ai %}
  {
    label: "Slash commands",
    href: ROUTES.SETTINGS_SLASH_COMMANDS,
    icon: Slash,
    description: "Custom shortcuts + built-in toggles",
  },
{%- endif %}
  {
    label: "Notifications",
    href: ROUTES.SETTINGS_NOTIFICATIONS,
    icon: Bell,
    description: "What we email you about",
  },
  {
    label: "Appearance",
    href: ROUTES.SETTINGS_APPEARANCE,
    icon: Palette,
    description: "Theme, density, brand color",
  },
];

export function SettingsNav() {
  const pathname = usePathname();
  const stripped = pathname.replace(/^\/[a-z]{2}/, "");

  return (
    <>
      <nav className="hidden lg:block">
        <ul className="space-y-1">
          {ITEMS.map((item) => {
            const active = stripped === item.href || stripped.startsWith(item.href + "/");
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={cn(
                    "group flex items-start gap-3 rounded-xl px-3 py-2.5 text-sm transition-colors",
                    active
                      ? "bg-foreground text-background"
                      : "text-foreground/65 hover:bg-foreground/5 hover:text-foreground",
                  )}
                >
                  <item.icon
                    className={cn(
                      "mt-0.5 h-4 w-4 shrink-0",
                      active ? "text-background" : "text-foreground/40 group-hover:text-foreground",
                    )}
                  />
                  <div className="min-w-0">
                    <p className="font-semibold">{item.label}</p>
                    <p
                      className={cn(
                        "mt-0.5 text-xs",
                        active ? "text-background/65" : "text-foreground/45",
                      )}
                    >
                      {item.description}
                    </p>
                  </div>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      <nav className="-mx-3 flex scrollbar-thin gap-1.5 overflow-x-auto px-3 pb-2 lg:hidden">
        {ITEMS.map((item) => {
          const active = stripped === item.href || stripped.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "border-foreground/15 inline-flex shrink-0 items-center gap-2 rounded-full border px-4 py-1.5 text-sm font-medium transition-colors",
                active
                  ? "bg-foreground text-background border-foreground"
                  : "text-foreground/65 hover:text-foreground hover:border-foreground/40",
              )}
            >
              <item.icon className="h-3.5 w-3.5" />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </>
  );
}
