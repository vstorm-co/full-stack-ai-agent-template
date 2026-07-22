"use client";

import { McpConnectionsManager } from "@/components/settings/mcp-connections-manager";

export default function IntegrationsSettingsPage() {
  return (
    <div className="space-y-6">
      <section className="border-border bg-card rounded-xl border">
        <header className="border-border border-b px-5 py-4">
          <h2 className="text-foreground text-sm font-semibold">Integrations</h2>
          <p className="text-muted-foreground mt-1 text-xs">
            Connect MCP servers to give your assistant extra tools — internal APIs, SaaS services,
            data sources.
          </p>
        </header>
        <div className="px-5 py-5">
          <McpConnectionsManager />
        </div>
      </section>
    </div>
  );
}
