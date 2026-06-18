import type { ReactNode } from "react";

import { PageHero } from "@/components/dashboard/page-hero";
import { SettingsNav } from "@/components/settings/settings-nav";

export default function SettingsLayout({ children }: { children: ReactNode }) {
  return (
    <div className="mx-auto w-full max-w-6xl space-y-6 pb-10">
      <PageHero
        eyebrow="Settings"
        title={
          <>
            Make it <em>yours.</em>
          </>
        }
        description="Personal account, appearance, notifications, slash commands."
      />

      <div className="grid gap-6 lg:grid-cols-[220px_1fr] lg:gap-10">
        <aside className="lg:sticky lg:top-6 lg:self-start">
          <SettingsNav />
        </aside>
        <div className="min-w-0">{children}</div>
      </div>
    </div>
  );
}
