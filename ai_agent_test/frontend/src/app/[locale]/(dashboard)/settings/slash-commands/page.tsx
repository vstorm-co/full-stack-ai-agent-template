"use client";

import { SettingsSection } from "@/components/settings/settings-section";
import { SlashCommandsManager } from "@/components/settings/slash-commands-manager";

export default function SlashCommandsSettingsPage() {
  return (
    <div className="space-y-6">
      <SettingsSection
        title="Slash commands"
        description="Customize the /command palette in chat — disable built-ins, or define your own quick prompts."
      >
        <SlashCommandsManager />
      </SettingsSection>
    </div>
  );
}
