"use client";

import { MemoryManager } from "@/components/settings/memory-manager";

export default function MemorySettingsPage() {
  return (
    <div className="space-y-6">
      <section className="border-border bg-card rounded-xl border">
        <header className="border-border border-b px-5 py-4">
          <h2 className="text-foreground text-sm font-semibold">Memory</h2>
          <p className="text-muted-foreground mt-1 text-xs">
            What the assistant remembers about you across conversations. You can see, edit, and
            delete everything it knows.
          </p>
        </header>
        <div className="px-5 py-5">
          <MemoryManager />
        </div>
      </section>
    </div>
  );
}
