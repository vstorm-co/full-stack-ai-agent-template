"use client";

import { SlashCommandsManager } from "@/components/settings/slash-commands-manager";

export default function SlashCommandsSettingsPage() {
  return (
    <div className="space-y-6">
      <section className="border-border bg-card rounded-xl border">
        <header className="border-border border-b px-5 py-4">
          <h2 className="text-foreground text-sm font-semibold">Slash commands</h2>
          <p className="text-muted-foreground mt-1 text-xs">
            Customize the /command palette in chat — disable built-ins, or define your own quick
            prompts.
          </p>
        </header>
        <div className="px-5 py-5">
          <SlashCommandsManager />
        </div>
      </section>
    </div>
  );
}
