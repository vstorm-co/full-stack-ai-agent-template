"use client";

import { SectionCard } from "@/components/settings/settings-section";
import { ThemeToggle } from "@/components/theme";

export default function AppearanceSettingsPage() {
  return (
    <div className="space-y-6">
      <SectionCard title="Theme" description="Light, dark, or follow your system preference.">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <p className="text-foreground text-sm font-medium">Color scheme</p>
            <p className="text-muted-foreground mt-0.5 text-xs leading-relaxed">
              Affects the entire dashboard. Marketing pages alternate sections regardless.
            </p>
          </div>
          <div className="shrink-0">
            <ThemeToggle variant="dropdown" />
          </div>
        </div>
      </SectionCard>
    </div>
  );
}
