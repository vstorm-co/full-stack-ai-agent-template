"use client";

import type { ReactNode } from "react";
import { Bell, {% if cookiecutter.enable_memory %}NotebookPen, {% endif %}Palette, {% if cookiecutter.enable_mcp_client %}Plug, {% endif %}Shield, Slash, UserCircle } from "lucide-react";

import { ROUTES } from "@/lib/constants";
import { PageHeader } from "@/components/dashboard/page-header";
import { PageTabs, type PageTab } from "@/components/dashboard/page-tabs";

const SETTINGS_TABS: PageTab[] = [
  { label: "Profile", href: ROUTES.SETTINGS_PROFILE, icon: UserCircle },
  { label: "Account", href: ROUTES.SETTINGS_ACCOUNT, icon: Shield },
  { label: "Slash commands", href: ROUTES.SETTINGS_SLASH_COMMANDS, icon: Slash },
{%- if cookiecutter.enable_mcp_client %}
  { label: "Integrations", href: ROUTES.SETTINGS_INTEGRATIONS, icon: Plug },
{%- endif %}
{%- if cookiecutter.enable_memory %}
  { label: "Memory", href: ROUTES.SETTINGS_MEMORY, icon: NotebookPen },
{%- endif %}
  { label: "Notifications", href: ROUTES.SETTINGS_NOTIFICATIONS, icon: Bell },
  { label: "Appearance", href: ROUTES.SETTINGS_APPEARANCE, icon: Palette },
];

export default function SettingsLayout({ children }: { children: ReactNode }) {
  return (
    <div className="space-y-6 pb-8">
      <PageHeader
        eyebrow="Settings"
        title="Settings"
        description="Manage your account, appearance, notifications, and slash commands."
      />
      <PageTabs tabs={SETTINGS_TABS} />
      <div className="min-w-0">{children}</div>
    </div>
  );
}
